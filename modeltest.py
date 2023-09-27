# coding: utf-8
import json, yaml


with open("../order-data/campaigns/run2_2018_pp_nano.yaml", "r") as f:
    cpn = yaml.full_load(f)

from order.models.campaign import Campaign

c = Campaign(**cpn)
