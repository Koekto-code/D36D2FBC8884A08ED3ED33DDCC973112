from bs4 import BeautifulSoup
import requests
import io
import json

def titleToInt(obj):
    try: return int(str(obj["title"]).replace(',', ''))
    except: return 0

# Accepts relative path to some repo
def parseGithubRepo(repo_name):
    # Download HTML page
    page = requests.get("https://github.com" + repo_name)

    soup = BeautifulSoup(page.text, features="html.parser")
    # Save data to dictionary to make clean JSON
    repodata = dict()
    
    # Parse data from bookmarks
    repodata['issues']        = titleToInt(soup.find(id="issues-repo-tab-count"))
    repodata['pull_requests'] = titleToInt(soup.find(id="pull-requests-repo-tab-count"))
    repodata['actions']       = titleToInt(soup.find(id="actions-repo-tab-count"))
    repodata['projects']      = titleToInt(soup.find(id="projects-repo-tab-count"))
    
    repodata['forks']         = titleToInt(soup.find(id="repo-network-counter"))
    repodata['stars']         = titleToInt(soup.find(id="repo-stars-counter-star"))
    # Broken on some pages
    # repodata['watchers']      = titleToInt(soup.find(id="repo-notifications-counter"))
    
    # Get latest commit comments (usually 2 similar things)
    shown_commits = [
        cmt for cmt in soup.find_all("a") if
            'data-test-selector' in cmt.attrs and
                cmt['data-test-selector'] == "commit-tease-commit-message"]

    repodata['latest_commit_comment'] = shown_commits[0].text
    
    return repodata

reponame = "/glfw/glfw"
repodata = parseGithubRepo(reponame)

with io.open("repo.json", 'w') as wfile:
   wfile.write(json.dumps(repodata))
