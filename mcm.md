## Towards an MCM adapter

We may need to parse MCM for some information in the future.  Scripts
are avialable to do this job at
[github.com/cms-PdmV/mcm_scripts](https://github.com/cms-PdmV/mcm_scripts/tree/master).
I copied the minimal code to do the job: the `order/mcm_rest.py` and
`tests/mcm_get_requests.py`.  The first one is enabling the MCM
connection. THe second one is to execute. Just two examples are
provided there:

1. Get a list of all `NanoAOD` campaign: 

```python campaigns =
mcm.get('campaigns', query='prepid=*NanoAOD*') 
``` 

This is equivalent to accessing the web page:
[https://cms-pdmv-prod.web.cern.ch/mcm/campaigns?prepid=*NanoAOD*](https://cms-pdmv-prod.web.cern.ch/mcm/campaigns?prepid=*NanoAOD*).
In fact the script would emulate the web access and it **will require
authentification with CERN SSO via Web**. This is
inconvenient... Maybe there is a better way. 

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
