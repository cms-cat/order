from order.mcm_rest import McM

mcm = McM(id='oidc', dev=False, debug=False)

print("List of campaigns:\n")
campaigns = mcm.get('campaigns', query='prepid=*NanoAOD*')
for camp in campaigns:
    print(camp['prepid'], camp['energy'])


myCampaign = "Run3Summer22NanoAODv12"
myProcess = "TT*"

print("\n List of requests and their process names in %s campaign, with mask 'dataset_name=%s'\n"%(myCampaign, myProcess))

campaign_requests = mcm.get('requests', query='member_of_campaign='+myCampaign+'&status=done&dataset_name='+myProcess)
for request in campaign_requests:
    print(request['prepid'], request['dataset_name'])

    
