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
    
    # Parse project languages
    lang_html_elem = soup.find(text="Languages")
    if lang_html_elem:
        lang_html_elem = lang_html_elem.parent
        if (not lang_html_elem):
            print("FAIL")
        lang_html_elem = lang_html_elem.parent
        if (not lang_html_elem):
            print("FAIL_FAIL")
         
        lang_dict = {}
        lang_soup = BeautifulSoup(str(lang_html_elem), features="html.parser") \
            .find_all(class_="Progress-item")
            
        for field in lang_soup:
            fdata = field["aria-label"].split(' ')
            percent = fdata[-1]
            lang_name = ''.join(fdata[:-1])
            lang_dict[lang_name] = float(percent)
        repodata['languages'] = lang_dict
    else:
        repodata['languages'] = dict()
    
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
    all_anchors = soup.find_all("a")
    shown_commits = [
        cmt for cmt in all_anchors if
        'data-test-selector' in cmt.attrs and
        cmt['data-test-selector'] == "commit-tease-commit-message"]
    
    if shown_commits:
        repodata['latest_commit_comment'] = shown_commits[0].text
    
    # a['data-hovercard-url'] has '/users/username/hovercard' form
    contributors = list(set([
        a['data-hovercard-url'].split('/')[2] for a in all_anchors if
        'data-hovercard-url' in a.attrs and
        '/users/' == a['data-hovercard-url'][:7]]))
    repodata['top_contrib'] = contributors
    
    return repodata

def getUserRepos(username: str):
    # Download HTML page
    page = requests.get("https://github.com/" + username + "?tab=repositories")
    
    # Get list of <a href="/user/repo">Name</a>
    user_repos = (
        BeautifulSoup(page.text, features="html.parser")
        .find_all(itemprop="name codeRepository"))
    repo_urls = [rep['href'] for rep in user_repos]
    return repo_urls

class RepoSummary:
    def __init__(self):
        self.data = {
            'languages': dict(),
            'contributors': list(),
        
            'issues': 0,
            'pull_requests': 0,
            'actions': 0,
            'projects': 0,
            'forks': 0,
            'stars': 0
        }
        
        self.repos_analyzed = 0
        self.parsed_repos = set()
        self.new_contributors = list()
        
        self.__finalized = False
    
    def __iadd__(self, rdata: dict):
        for lang in rdata['languages']:
            if not lang in self.data['languages']:
                self.data['languages'][lang] = 0.0
            self.data['languages'][lang] += rdata['languages'][lang]
        
        # Find only new contributors to parse their repos later
        contrib_updated = set(self.data['contributors']).union(rdata['top_contrib'])
        self.new_contributors = list(contrib_updated - set(self.data['contributors']))
        self.data['contributors'] = contrib_updated
        
        for fieldname in ['issues', 'pull_requests', 'actions', 'forks', 'stars']:
            self.data[fieldname] += rdata[fieldname]
        
        self.repos_analyzed += 1
        return self
    
    # Finalize just once per instance
    def finalize(self):
        if self.__finalized:
            return
        
        for lang in self.data['languages']:
            self.data['languages'][lang] /= self.repos_analyzed
        
        for fieldname in ['issues', 'pull_requests', 'actions', 'forks', 'stars']:
            self.data[fieldname] /= self.repos_analyzed
        self.__finalized = True

def collectData(repoBegin: str, maxDepth: int, showProgress = True):
    reponames = set([repoBegin])
    summary = RepoSummary()

    while True:
        if not reponames: break
        repodata = []
        for name in reponames:
            if (len(repodata) < maxDepth - summary.repos_analyzed):
                if showProgress:
                    print('Parsing', name, end='...\n')
                repodata.append(parseGithubRepo(name))
                summary.parsed_repos.add(name)
        
        reponames = set()
        for rep in repodata:
            summary += rep
            for con in summary.new_contributors:
                reponames = reponames.union(getUserRepos(con))
        reponames -= summary.parsed_repos
    
    if showProgress:
        print('')
    return summary

