import argparse
# from az.cli import az  # Uncommented as requested
import os
import logging
import requests
from dotenv import load_dotenv
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Get environment variables
personal_access_token = os.getenv('PERSONAL_ACCESS_TOKEN')
organization_url = os.getenv('ORGANIZATION_URL')
project_name = os.getenv('PROJECT_NAME')

# Encode the PAT in Base64
encoded_pat = base64.b64encode(f":{personal_access_token}".encode()).decode()

# Helper function to make authenticated requests
def make_request(url, method='GET', data=None):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_pat}'
    }
    if method == 'GET':
        response = requests.get(url, headers=headers)
    elif method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e.msg}")
        logging.error(f"Response content: {response.text}")
        raise
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error: {e}")
        logging.error(f"Response content: {response.text}")
        raise

# Get the ID's of each Pull Request from the input file and create an array
def getIdAndRepoOfPRsInArray(file_name):
    prs = []
    with open(file_name, 'r') as f:
        lines = f.readlines()
    for line in lines:
        parts = line.strip().split('/')
        repo = parts[6]
        pr_id = parts[-1]
        prs.append({
            'repo': repo,
            'id': pr_id,
            'link': line.strip()  # Add the link to the dictionary
        })
    return prs

def get_pull_request_commits(repository_name, pull_request_id):
    logging.info(f"Fetching commits for PR {pull_request_id} in repo {repository_name}")
    url = f"{organization_url}/{project_name}/_apis/git/repositories/{repository_name}/pullRequests/{pull_request_id}/commits?api-version=7.1-preview.1"
    logging.info(f"Constructed URL: {url}")
    commits = make_request(url)
    if not commits['value']:
        logging.error(f"No commits found for PR {pull_request_id} in repo {repository_name}")
        raise ValueError(f"No commits found for PR {pull_request_id} in repo {repository_name}")
    target_commit_id = commits['value'][0]['commitId']
    base_commit_id = commits['value'][-1]['commitId']
    logging.info(f"Base commit ID: {base_commit_id}, Target commit ID: {target_commit_id}")
    return base_commit_id, target_commit_id

def get_commit_diffs(repository_name, base_commit_id, target_commit_id):
    if base_commit_id == target_commit_id:
        logging.warning(f"Base and target commit IDs are the same for repo {repository_name}")
        return []
    logging.info(f"Fetching commit diffs between {base_commit_id} and {target_commit_id} in repo {repository_name}")
    url = f"{organization_url}/{project_name}/_apis/git/repositories/{repository_name}/diffs/commits?baseVersion={base_commit_id}&targetVersion={target_commit_id}&api-version=7.1-preview.1"
    logging.info(f"Constructed URL for diffs: {url}")
    commit_diffs = make_request(url)
    changed_files = [change['item']['path'] for change in commit_diffs['changes']]
    logging.info(f"Changed files: {changed_files}")
    return changed_files

def changes_are_similar(changed_files):
    similar = any("azure-pipelines.yml" in file or "k8-repo-name" in file for file in changed_files)
    logging.info(f"Changes are similar: {similar}")
    return similar

def compare_changes(prs):
    similar_prs = []
    dissimilar_prs = []
    for pr in prs:
        try:
            base_commit_id, target_commit_id = get_pull_request_commits(pr['repo'], pr['id'])
            if base_commit_id == target_commit_id:
                logging.info(f"Skipping PR {pr['id']} in repo {pr['repo']} as there are no changes.")
                continue
            changed_files = get_commit_diffs(pr['repo'], base_commit_id, target_commit_id)
            if changes_are_similar(changed_files):
                similar_prs.append(pr)
            else:
                dissimilar_prs.append(pr)
        except ValueError as e:
            logging.error(e)
    return similar_prs, dissimilar_prs

# Approve the PR's for each of the ID's in the array
def approvePRs(prs):
    similar_prs, dissimilar_prs = compare_changes(prs)
    for pr in similar_prs:
        logging.info(f"Approving PR {pr['id']} in repo {pr['repo']}")
        print(f"az repos pull-request approve --repo {pr['repo']} --pull-request-id {pr['id']}")
        # az("repos", "pull-request", "approve", "--repo", pr['repo'], "--pull-request-id", pr['id'])
    if dissimilar_prs:
        logging.info("PRs with dissimilar changes:")
        for pr in dissimilar_prs:
            if 'link' in pr:
                logging.info(f"PR link: {pr['link']}")
            else:
                logging.info(f"PR ID: {pr['id']} in repo {pr['repo']}")

# Reject the PR's for each of the ID's in the array
def rejectPRs(prs):
    for pr in prs:
        logging.info(f"Rejecting PR {pr['id']} in repo {pr['repo']}")
        print(f"az repos pull-request reject --repo {pr['repo']} --pull-request-id {pr['id']}")
        # az("repos", "pull-request", "reject", "--repo", pr['repo'], "--pull-request-id", pr['id'])

def main():
    parser = argparse.ArgumentParser(description="Approve or Reject Pull Requests from a file.")
    parser.add_argument('--approve', action='store_true', help="Approve the pull requests.")
    parser.add_argument('--reject', action='store_true', help="Reject the pull requests.")
    parser.add_argument('file_name', type=str, help="File containing pull request URLs.")

    args = parser.parse_args()

    prs = getIdAndRepoOfPRsInArray(args.file_name)

    if args.approve:
        approvePRs(prs)
    elif args.reject:
        rejectPRs(prs)
    else:
        logging.info("Please use --help to see list of options.")

if __name__ == "__main__":
    main()