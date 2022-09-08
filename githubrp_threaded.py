from bs4 import BeautifulSoup
import requests
import io
import json
import threading as mt

def titleToInt(obj):
    try: return int(str(obj["title"]).replace(',', ''))
    except: return 0

# Accepts relative path to some repo
def parseGithubRepo(repo_name: str, showProgress: bool):
    # Download HTML page
    if showProgress:
        print(f"Parsing {repo_name}...")
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
    
    if showProgress:
        print(f"Done parsing of {repo_name}")
    return repodata

def getUserRepos(username: str, showProgress: bool):
    # Download HTML page
    if showProgress:
        print(f"Getting repos of {username}...")
    page = requests.get("https://github.com/" + username + "?tab=repositories")
    
    # Get list of <a href="/user/repo">Name</a>
    user_repos = (
        BeautifulSoup(page.text, features="html.parser")
        .find_all(itemprop="name codeRepository"))
    repo_urls = [rep['href'] for rep in user_repos]
    print(f"Done getting repos of {username}")
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

def collectData(repoBegin: str, targetDepth: int, numThreads = 1, showProgress = True):
    reponames = [repoBegin]
    summary = RepoSummary()

    def appendParsedRepo(name: str, showProgress: bool, target: list):
        target.append(parseGithubRepo(name, showProgress))
    
    def updateReponames(con: str, showProgress: bool, target: set):
        target.update(getUserRepos(con, showProgress))

    while True:
        if not reponames: break

        ### Begin multithreaded block
        repodata = []
        for nm in range(0, len(reponames), numThreads):
            if len(repodata) < targetDepth - summary.repos_analyzed:
                threads = []
                for threadnum in range(numThreads):
                    if len(reponames) > nm + threadnum:
                        threads.append(mt.Thread(
                            target=appendParsedRepo,
                            args=(reponames[nm + threadnum], showProgress, repodata)
                        ))
                        summary.parsed_repos.add(reponames[nm])
                
                for thr in threads:
                    thr.start()
                for thr in threads:
                    thr.join()
        ### End multithreaded block
        
        ### Begin multithreaded block
        reponames = set()
        for rep in repodata:
            summary += rep
            for ncon in range(0, len(summary.new_contributors), numThreads):
                threads = []
                for threadnum in range(numThreads):
                    if len(summary.new_contributors) > ncon + threadnum:
                        threads.append(mt.Thread(
                            target=updateReponames,
                            args=(summary.new_contributors[ncon + threadnum],
                                  showProgress,
                                  reponames)
                        ))
                for thr in threads:
                    thr.start()
                for thr in threads:
                    thr.join()

        reponames -= summary.parsed_repos
        reponames = list(reponames)
        ### End multithreaded block

        # for rep in repodata:
        #     summary += rep
        #     for con in summary.new_contributors:
        #         reponames.update(getUserRepos(con))
    
    if showProgress:
        print('')
    return summary

