
import cli

try:
    from utility.logger import logger
except:
    print('++Using local logger.++')

if __name__ == "__main__":
    config = {'General': {'workload': 'TEST', 'iterations': '3', 'suite_version': 'BMK-1642'}, 'HEPscore': {'site': 'test', 'results_file': 'REPLACE_summary.json', 'gpu': 'true', 'wl_version': 'ci_v0.2', 'plugins': 'f,l,m,s,p,g,u,v', 'others': ''}, 'Scan': {'threads': '4', 'copies': '1,2'}, 'ExtraArgs': {'device': 'cuda', 'n-objects': '1000,5000,10000'}}

    cli.print_status()