## Towards an MCM adapter

We may need to parse MCM for some information in the future.  Scripts
are avialable to do this job at
[github.com/cms-PdmV/mcm_scripts](https://github.com/cms-PdmV/mcm_scripts/tree/master).
I copied the minimal code to do the job: the `order/mcm_rest.py` and
`tests/mcm_get_requests.py`.  The first one is enabling the MCM
connection. The second one is to execute. Just two examples are
provided there:

1. Get a list of all `NanoAOD` campaigns: 

```python campaigns =
mcm.get('campaigns', query='prepid=*NanoAOD*') 
``` 

This is equivalent to accessing the web page:
[https://cms-pdmv-prod.web.cern.ch/mcm/campaigns?prepid=*NanoAOD*](https://cms-pdmv-prod.web.cern.ch/mcm/campaigns?prepid=*NanoAOD*).
In fact, the script would emulate the web access and it **will require
authentification with CERN SSO via Web Browser**. This is
inconvenient... Maybe there is a better way, but I do not know of it.

2. Get a list of requests in a given campaign, where dataset starts with `TT`:

```
campaign_requests = mcm.get('requests', query='member_of_campaign=Run3Summer22NanoAODv12&status=done&dataset_name=TT*')
```

This is equivalent to accessing this page:
[https://cms-pdmv-prod.web.cern.ch/mcm/requests?dataset_name=TT*&member_of_campaign=Run3Summer22NanoAODv12](https://cms-pdmv-prod.web.cern.ch/mcm/requests?dataset_name=TT*&member_of_campaign=Run3Summer22NanoAODv12)

Test the script:
```shell
python tests/mcm_get_requests.py
```


## Link between MCM and DAS

One can query DAS and find the **full** dataset name, knowing the `prepid` in MCM, like so:
```shell
dasgoclient -query="dataset prepid=GEN-Run3Summer22NanoAODv12-00010"

"""
/TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2/NANOAODSIM
"""
```

One could also get the MCM prepid of a dataset from DAS, like so:
```shell
dasgoclient -query="mcm dataset=/TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2/NANOAODSIM"

"""
GEN-Run3Summer22NanoAODv12-00010*
"""
```
