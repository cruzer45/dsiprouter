import os
from flask import Blueprint, render_template, abort, jsonify
from util.security import api_security
from database import SessionLoader, DummySession, dSIPMultiDomainMapping
from shared import showApiError,debugEndpoint,StatusCodes
from enum import Enum
import importlib.util
import settings, globals



class FLAGS():
    FUSIONPBX_PLUGIN = "fusion"
    FREEPBX_PLUGIN = "freepbx"


mediaserver = Blueprint('mediaserver','__name__')

@mediaserver.route('/api/v1/mediaserver/domain/',methods=['GET'])
@mediaserver.route('/api/v1/mediaserver/domain/<string:config_id>',methods=['GET'])
@api_security
def getDomains(config_id=None):
    """
    List all of the domains on a PBX\n
    If the PBX only contains a single domain then it will return the hostname or ip address of the system.
    If the PBX is multi-tenant then a list of all domains will be returned

    ===============
    Request Payload
    ===============

    .. code-block:: json


    {}

    ================
    Response Payload
    ================

    .. code-block:: json

        {
            error: <string>,
            msg: <string>,
            kamreload: <bool>,
            data: [
                domains: [
                    {
                    domain_id: <int>,
                    name: <string>,
                    enabled: <string>,
                    description: <string>
                    }
                ]
            ]
        }
    """

    # Determine which plug-in to use
    # Currently we only support FusionPBX
    # Check if Configuration ID exists

    db = DummySession()

    response_payload = {'error': '', 'msg': '', 'kamreload': globals.reload_required, 'data': []}

    try:
        if settings.DEBUG:
            debugEndpoint()

        db = SessionLoader()

        if config_id != None:
            domainMapping = db.query(dSIPMultiDomainMapping).filter(dSIPMultiDomainMapping.pbx_id == config_id).first()
            if (domainMapping) is not None:
                response_payload['msg'] = 'Domain Configuration Exists'

                if domainMapping.type == int(dSIPMultiDomainMapping.FLAGS.TYPE_FUSIONPBX.value):
                    plugin = FLAGS.FUSIONPBX_PLUGIN
                elif domainMapping.type == dSIPMultiDomainMapping.FLAGS.TYPE_FUSIONPBX_CLUSTER.value:
                    plugin = FLAGS.FUSIONPBX_PLUGIN
                elif domainMapping.type == dSIPMultiDomainMapping.FLAGS.TYPE_FREEPBX.value:
                    plugin = FLAGS.FREEPBX_PLUGIN;
                    raise Exception("FreePBX Plugin is not supported yet")
                else:
                    raise Exception("PBX plugin for config #{} can not be found".format(config_id))


                # Import plugin

                # Returns the Base directory of this file
                base_dir = os.path.dirname(__file__)

                # Use the Base Dir to specify the location of the plugin required for this domain
                spec = importlib.util.spec_from_file_location(plugin, "{}/plugin/{}/interface.py".format(base_dir,plugin))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Create instance of Media Server Class
                mediaserver = module.mediaserver(hostname=domainMapping.db_host,username=domainMapping.db_username, \
                                                password=domainMapping.db_password, \
                                                dbname="fusionpbx" \
                                                )
                # Get a Connection to the Media Server
                conn = mediaserver.getConnection()

                # Todo
                # Use plugin to get list of domains by calling plugin.<pbxtype>.getDomains()

            else:
                response_payload['msg'] = 'No domain configuration exists for config #{}'.format(config_id)
        else:
            raise Exception("The configuration id must be provided")


        #db.commit()

        return jsonify(response_payload), StatusCodes.HTTP_OK

    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()



@mediaserver.route('/api/v1/mediaserver/domain',methods=['POST'])
@api_security
def postDomains():
    result = "{ \
        domain_id: 1012 \
        name: AprilandMackCo, \
        enabled: true, \
        description: 'April and Mack Co', \
        config_id: 64 \
        }"
    return result;
