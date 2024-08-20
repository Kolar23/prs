import subprocess
import argparse

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
            'id': pr_id
        })
    return prs

# Approve the PR's for each of the ID's in the array
def approvePRs(prs):
    for pr in prs:
        print(f"Approving PR {pr['id']} in repo {pr['repo']}")
        subprocess.run([
            "az", "repos", "pr", "set-vote",
            "--id", pr['id'],
            "--vote", "approve",
            "--organization", "https://dev.azure.com/TireBuyer",
        ])

# Reject the PR's for each of the ID's in the array
def rejectPRs(prs):
    for pr in prs:
        print(f"Rejecting PR {pr['id']} in repo {pr['repo']}")
        subprocess.run([
            "az", "repos", "pr", "set-vote",
            "--id", pr['id'],
            "--vote", "reject",
            "--organization", "https://dev.azure.com/TireBuyer",
        ])

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
        print("Please use --help to see list of options.")

if __name__ == "__main__":
    main()