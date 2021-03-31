#!/usr/bin/python

# Base imports for all integrations, only remove these at your own risk!
import json
import sys
import os
import time
import pandas as pd
from collections import OrderedDict

from integration_core import Integration

from IPython.core.magic import (Magics, magics_class, line_magic, cell_magic, line_cell_magic)
from IPython.core.display import HTML


import taxii2client.v20
import stix2

#import IPython.display
from IPython.display import display_html, display, Javascript, FileLink, FileLinks, Image
import ipywidgets as widgets

@magics_class
class Taxii(Integration):
    # Static Variables
    # The name of the integration
    name_str = "taxii"
    instances = {}
    custom_evars = ['taxii_conn_default', 'taxii_group_collections', 'taxii_verify_ssl', 'taxii_suppress_https_warnings', 'taxii_path_to_certs']
    # These are the variables in the opts dict that allowed to be set by the user. These are specific to this custom integration and are joined
    # with the base_allowed_set_opts from the integration base

    # These are the variables in the opts dict that allowed to be set by the user. These are specific to this custom integration and are joined
    # with the base_allowed_set_opts from the integration base
    custom_allowed_set_opts = ["taxii_conn_default", "taxii_verify_ssl", "taxii_suppress_https_warnings", "taxii_path_to_certs", "taxii_group_collections"]



    allowed_ops = ['=', '!=', 'in', '>', '<', '>=', '<=', 'contains']

    myopts = {}
    myopts['taxii_conn_default'] = ["default", "Default instance to connect with"]
    myopts['taxii_verify_ssl'] = [True, "Verify SSL connection is valid"]
    myopts['taxii_suppress_https_warnings'] = [0, "Hide warnings about SSL issues"]
    myopts['taxii_path_to_certs'] = ["", "Path to custom SSL bundle for taxii connections"]
    myopts['taxii_group_collections'] = [0, "Group collections got query, if 0, we add fields: collection name and collection_id - May take longer"]


    # Class Init function - Obtain a reference to the get_ipython()
    def __init__(self, shell, debug=False, *args, **kwargs):
        super(Taxii, self).__init__(shell, debug=debug)
        self.debug = debug

        #Add local variables to opts dict
        for k in self.myopts.keys():
            self.opts[k] = self.myopts[k]

        self.load_env(self.custom_evars)
        self.parse_instances()

    def customDisconnect(self, instance):
        self.instances[instance]['session'] = None
        self.instances[instance]['connected'] = False
        self.instances[instance]['server'] = None
        self.instances[instance]['api_root'] = None
        self.instances[instance]['taxii_collections'] = None

    def customAuth(self, instance):
        result = -1
        inst = None
        breqAuth = False

        # JUPYTER_TAXII_CONN_URL_DEFAULT="https://cti-taxii.mitre.org/taxii"
        # %taxiiuser@https://cti-taxii.mitre.org:443?path=/taxii&useproxy=1&authreq=0

        if self.opts['taxii_suppress_https_warnings'][0] == 1:
            import warnings
            warnings.filterwarnings('ignore', "Unverified HTTPS request is being made")

        if instance not in self.instances.keys():
            result = -3
            print("Instance %s not found in instances - Connection Failed" % instance)
        else:
            inst = self.instances[instance]

        if inst is not None:
            if inst['options'].get('useproxy', 0) == 1:
                proxystr = self.get_proxy_str(instance)
                if self.debug:
                    print("Proxy String: %s" % proxystr)

                prox_pass = self.get_proxy_pass(proxystr, instance)
                proxurl = proxystr.replace("@", ":" + prox_pass + "@")
                proxies = {'http': proxurl, 'https': proxurl}
                inst['proxies'] = proxies
            else:
                inst['proxies'] = None
            if 'authreq' in inst['options']:
                if inst['options']['authreq'] == True or inst['options']['authreq'] == 1:
                    breqAuth = True

            if self.opts['taxii_verify_ssl'][0] == 0 or self.opts['taxii_verify_ssl'][0] == False:
                myverify = False
            else:
                myverify = True

            if self.debug:
                print("myverify: %s" % myverify)

            myurl = inst['scheme'] + "://" + inst['host'] + ":" + str(inst['port']) + inst['options'].get('path', '/')
            inst['full_url'] = myurl
            if self.debug:
                print(inst['full_url'])
            inst['session'] = None
            if breqAuth:
                print("Taxii Auth not yet handled")
            else:
                try:
                    inst['server'] = taxii2client.v20.Server(inst['full_url'], verify=myverify, proxies=inst['proxies'])
                    inst['api_root'] = inst['server'].api_roots[0] # Maybe do multiple?
                    inst['taxii_collections'] = []

                    for tc in inst['api_root'].collections:
#                        inst['taxii_collections'].append(stix2.TAXIICollectionSource(tc))
                        inst['taxii_collections'].append(tc)
                        if self.debug:
                            print("Added %s (ID: %s) to collections" % (tc.title, tc.id))
                    result = 0
                except Exception as e:
                    print("Unable to connect to Taxii instance %s at %s" % (instance, inst["conn_url"]))
                    print("Exception: %s" % e)
                    result = -2
        return result


######## Where I got


    def validateQuery(self, query, instance):
        bRun = True
        bReRun = False

        if self.instances[instance]['last_query'] == query:
            # If the validation allows rerun, that we are here:
            bReRun = True
        # Ok, we know if we are rerun or not, so let's now set the last_query 
        self.instances[instance]['last_query'] = query

        curquery = self.formatQuery(query)
        for q in curquery:
            if q[1] not in self.allowed_ops:
                print("Query ['%s' '%s' '%s'] using an operator (%s) that is not supported (%s) - Query may fail or produce unwanted results" % (q[0], q[1], q[2], q[1], self.allowed_ops))
                print("Query not submitted")
                bRun = False



        # Example Validation

        # Warn only - Don't change bRun
        # Basically, we print a warning but don't change the bRun variable and the bReRun doesn't matter
        # Warn and do not allow submission There is no way for a user to submit this query
#        if query.lower().find('limit ") < 0:
#            print("ERROR - All queries must have a limit clause - Query will not submit without out")
#            bRun = False
        return bRun


    def req_password(self, instance):

        bAuth = self.instances[instance]['options'].get('authreq', 0)
        if int(bAuth) == 0:
            bAuth = False
        if int(bAuth) == 1:
            bAuth = True
        return bAuth

    def req_username(self, instance):
        bAuth = self.instances[instance]['options'].get('authreq', 0)
        if int(bAuth) == 0:
            bAuth = False
        elif int(bAuth) == 1:
            bAuth = True
        return bAuth

    def formatQuery(self, query):
        retfilter = []
        qlines = query.strip().split("\n")
        for ql in qlines:
            qi = ql.split(" ")
            qprop = qi[0].strip()
            qop = qi[1].strip()
            qval = " ".join(qi[2:]).strip()
            if self.debug:
                print("'%s'  '%s'  '%s'" % (qprop, qop, qval))
            retfilter.append([qprop, qop, qval])
        return retfilter
    def retQueryFilter(self, qlist):
        retval = []
        for q in qlist:
            retval.append(stix2.Filter(q[0], q[1], q[2]))
        return retval

    def customQuery(self, query, instance, reconnect=True):

        mydf = None
        status = ""
        str_err = ""
        out_res_df = pd.DataFrame()
        inst = self.instances[instance]
        qlist = self.formatQuery(query)
        qfilter = self.retQueryFilter(qlist)
        try:
            if self.opts['taxii_group_collections'][0] == 1:
                searcher = stix2.CompositeDataSource()
                searcher.add_data_sources([stix2.TAXIICollectionSource(c) for c in inst['taxii_collections']])
                tres = searcher.query(qfilter)
                for r in tres:
                    try:
                        tdf = pd.json_normalize(json.loads(r.serialize()))
                        if len(tdf) > 0:
                            out_res_df = pd.concat([out_res_df, tdf], ignore_index=True)
                    except Exceptions as e:
                        if self.debug:
                            print("Error grouped: %s" % e)
            else:
                for c in inst['taxii_collections']:
                    c_title = c.title
                    c_id = c.id
                    searcher = stix2.CompositeDataSource()
                    searcher.add_data_sources([stix2.TAXIICollectionSource(c)])
                    tres = searcher.query(qfilter)
                    for r in tres:
                        try:
                            tdf = pd.json_normalize(json.loads(r.serialize()))
                            if len(tdf) > 0:
                                tdf['collection_name'] = c_title
                                tdf['collection_id'] = c_id
                                out_res_df = pd.concat([out_res_df, tdf], ignore_index=True)
                        except Exception as e:
                            if self.debug:
                                print("Error ungrouped: %s" % e)
            if len(out_res_df) == 0:
                mydf = None
                str_err = "Success - No Results"
            elif len(out_res_df) > 0:
                mydf = out_res_df
                str_err = "Success"
        except Exception as e:
            mydf = None
            str_err = str(e)

        if str_err.find("Success") >= 0:
            pass
        elif str_err.find("Session is not logged in") >= 0: # Need to fix this
            # Try to rerun query
            if reconnect == True:
                self.disconnect(instance)
                self.connect(instance)
                m, s = self.customQuery(query, instance, False)
                mydf = m
                status = s
            else:
                mydf = None
                status = "Failure - Session not logged in and reconnect failed"
        else:
            status = "Failure - query_error: " + str_err
        return mydf, status


# Display Help can be customized
    def customHelp(self):
        self.displayIntegrationHelp()
        self.displayQueryHelp('external_references.external_id = T1134.001')


    def displayQueryHelp(self, q_example):
        n = self.name_str
        m = "%" + self.name_str
        mq = "%" + m
        print("")
        print("Running queries with %s" % mq)
        print("###############################################################################################")
        print("")
        print("When running queries with %s, %s will be on the first line of your cell, with an optional instance and the next line is the query you wish to run. Example:" % (mq, mq))
        print("")
        print(mq)
        print(q_example)
        print("")
        print(mq + " myinstance")
        print(q_example)
        print("")
        print("Some query notes:")
        print("A Taxii Filter is 'property' 'operator' value' as seen above")
        print("- You may use multiple lines of filters, they are ANDed together")
        print("- operator must be in %s" % self.allowed_ops)
        print("- If the number of results is less than display_max_rows, then the results will be diplayed in your notebook")
        print("- You can change display_max_rows with %s set display_max_rows 2000" % m)
        print("- The results, regardless of being displayed will be placed in a Pandas Dataframe variable called prev_%s_<instance>" % n)
        print("- prev_%s_<instance> is overwritten every time a successful query is run. If you want to save results assign it to a new variable" % n)





    # This is the magic name.
    @line_cell_magic
    def taxii(self, line, cell=None):
        if cell is None:
            line = line.replace("\r", "")
            line_handled = self.handleLine(line)
            if self.debug:
                print("line: %s" % line)
                print("cell: %s" % cell)
            if not line_handled: # We based on this we can do custom things for integrations. 
                if line.lower() == "testintwin":
                    print("You've found the custom testint winning line magic!")
                else:
                    print("I am sorry, I don't know what you want to do with your line magic, try just %" + self.name_str + " for help options")
        else: # This is run is the cell is not none, thus it's a cell to process  - For us, that means a query
            self.handleCell(cell, line)

