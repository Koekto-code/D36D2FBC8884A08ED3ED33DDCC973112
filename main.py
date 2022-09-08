#import github_repo_parser as rp
import githubrp_threaded as rp
import time

def main():
    tpoint1 = time.time()
    # Collect data around GLFW repo.
    # Target number of parsed repos = 30
    # Threads = 8
    summary = rp.collectData('/glfw/glfw', 80, 8)
    tpoint2 = time.time()
    print(f"Parsing elapsed {round(tpoint2 - tpoint1, 5)} seconds.")
    
    # Make average from stored values
    summary.finalize()
    print("Analyzed", summary.repos_analyzed, "repos.")
    # for repo in summary.parsed_repos:
        # print(repo)
    
    print("Language percentage:")
    for lang in summary.data['languages']:
        percent = round(summary.data['languages'][lang], 4)
        print(lang + ": " + str(percent) + "%")
    
    print("Contributors:")
    for con in summary.data['contributors']:
        print(' ', con)
    
    print("Average values (units per repo):")
    print("  Issues:", round(summary.data['issues'], 2))
    print("  Pull requests:", round(summary.data['pull_requests'], 2))
    print("  Actions:", round(summary.data['actions'], 2))
    print("  Projects:", round(summary.data['projects'], 2))
    print("  Forks:", round(summary.data['forks'], 2))
    print("  Stars:", round(summary.data['stars'], 2))

main()