#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

some fields we often use
===============================================
field	     e.g.
brand        google
version      6.0.1
sdk	         23
serial	     0642f8d6f0ec9d1a
model        Nexus 5
....         ...
===============================================
"""

import logging

from tinydb import TinyDB, where
from tinydb.storages import MemoryStorage, JSONStorage
import requests
import re
from Public.ReadConfig import ReadConfig

logger = logging.getLogger(__name__)

TinyDB.DEFAULT_STORAGE = MemoryStorage

token = ReadConfig().get_server_token()


class atxserver2(object):
    """
    According to users requirements to select devices
    """

    def __init__(self, url):
        """
        Construct method
        """
        self._db = TinyDB(storage=MemoryStorage)
        if url and re.match(r"(http://)?(\d+\.\d+\.\d+\.\d+:\d+)", url):
            if '://' not in url:
                url = 'http://' + url
            else:
                url = url
            self._url = url
            self.load()
        else:
            logger.error('Atx server addr error')
        self.load()

    def load(self, **kwargs):
        """
        Use the data which got from stf platform to crate query db

        :return: the len of records in the db's table
        """
        kwargs['headers'] = {"Authorization": "Bearer " + token}
        res = requests.get(self._url + '/api/v1/devices', **kwargs).json()
        if res is not None:
            eids = self._db.insert_multiple(res['devices'])
            return len(eids)
        else:
            return 0

    def find(self, cond=None):
        """
        According condition to filter devices and return
        :param cond: condition to filter devices
        :type cond: where
        :return: stf_selector object and its db contains devices
        """
        if cond is not None:
            res = self._db.search(cond)
            self.purge()
            self._db.insert_multiple(res)
        return self

    def devices(self):
        """
        return all devices that meeting the requirement
        :return: list of devices
        """
        return self._db.all()

    def refresh(self):
        """
        reload the devices info from stf
        :return: the len of records in the db's table
        """
        self.purge()
        return self.load()

    def count(self):
        """
        count the records in the db's table
        :return: the len of records in the db's table
        """
        return len(self._db.all())

    def purge(self):
        """
        remove all the data from the db
        :return:
        """
        self._db.purge()

    def online_devices(self):
        '''查找online 的设备'''
        self.refresh()
        devices = self.find(where('present') == True).devices()
        if len(devices) > 0:
            return devices
        else:
            return False

    def present_ios_devices(self, **kwargs):
        kwargs['headers'] = {"Authorization": "Bearer " + token}
        self.refresh()
        self.find(where('platform') == 'apple').devices()
        devices = self.find(where('present') == True).devices()
        if len(devices) > 0:
            return [requests.get(self._url + '/api/v1/user/devices/' + device['udid'], **kwargs).json()['device'] for
                    device in devices]
        else:
            return False

    def present_android_devices(self, **kwargs):
        kwargs['headers'] = {"Authorization": "Bearer " + token}
        self.refresh()
        self.find(where('platform') == 'android').devices()
        devices = self.find(where('present') == True).devices()
        if len(devices) > 0:
            return [requests.get(self._url + '/api/v1/user/devices/' + device['udid'], **kwargs).json()['device'] for
                    device in devices]
        else:
            return False

    def present_udid_devices(self, **kwargs):
        kwargs['headers'] = {"Authorization": "Bearer " + token}
        present_udid_devices_list = []
        for udid in ReadConfig().get_server_udid():
            self.refresh()
            self.find(where('udid') == udid).devices()
            device = self.find(where('present') == True).devices()
            if device:
                present_udid_devices_list.append(
                    requests.get(self._url + '/api/v1/user/devices/' + udid, **kwargs).json()['device'])
            else:
                pass
        if len(present_udid_devices_list) > 0:
            return present_udid_devices_list
        else:
            return False

    def using_device(self, udid, **kwargs):
        kwargs['headers'] = {"Authorization": "Bearer " + token}
        # kwargs['json'] = {"udid": udid}
        ret = requests.post(self._url + '/api/v1/user/devices', json={"udid": udid, "idleTimeout": 7200}, **kwargs)
        if ret.status_code == 200:
            print(ret.json())
            return True
        else:
            return False

    def release_device(self, udid, **kwargs):
        kwargs['headers'] = {"Authorization": "Bearer " + token}
        ret = requests.delete(self._url + '/api/v1/user/devices/' + udid, **kwargs)
        if ret.status_code == 200:
            print(ret.json())
            return True
        else:
            return False


# if __name__ == '__main__':
#     import json
#     import time
#
#     # print(atxserver2('http://192.168.3.41:4000').using_device('ce051715b2ef600802'))
#     # time.sleep(4)
#     # print(atxserver2('http://192.168.3.41:4000').release_device('ce051715b2ef600802'))
#     print(json.dumps(atxserver2('http://192.168.3.41:4000').present_udid_devices()))
