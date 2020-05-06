import time
import os
import zipfile

from multiprocessing import Pool
import uiautomator2 as u2

# from Public.Devices import *    # for循环 check_alive  比较慢
from Public.Devices_new import *  # 多进程 check_alive ，Mac下需要配置  `export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`到环境变量

from Public.RunCases import RunCases
from Public.RunMaxim import RunMaxim
from Public.ReportPath import ReportPath
from Public.BasePage import BasePage
from Public.maxim_monkey import Maxim
from Public.Log import Log
from Public.ReadConfig import ReadConfig
from Public.chromedriver import ChromeDriver
from Public.Test_data import generate_test_data
from Public.Report import create_statistics_report, backup_report
from Public.ATX_Server import ATX_Server
from Public.atxserver2 import atxserver2

"""
- Drivers.py  设备的获取，初始化准备，测试执行都是在这里完成的
"""

def check_devives():
    # 根据method 获取android设备
    method = ReadConfig().get_method().strip()
    if method == 'SERVER':
        # get ATX-Server Online devices
        # devices = ATX_Server(ReadConfig().get_server_url()).online_devices()
        print('Get available online devices from ATX-Server...')
        devices = get_online_devices(ATX_Server(ReadConfig().get_server_url()).online_devices())
        print('\nThere has %s online devices in ATX-Server' % len(devices))

    elif method == 'SERVER2':
        print('Get available online devices from atxserver2...')
        devices = atxserver2_online_devices(atxserver2(ReadConfig().get_server_url()).present_android_devices())
        print('\nThere has %s online devices in atxserver2' % len(devices))

    elif method == 'UDID':
        print('Get available UDID devices %s from atxserver2...' % ReadConfig().get_server_udid())
        devices = atxserver2_online_devices(atxserver2(ReadConfig().get_server_url()).present_udid_devices())
        print('\nThere has %s available udid devices in atxserver2' % len(devices))

    elif method == 'IP':
        # get  devices from config devices list
        print('Get available IP devices %s from config... ' % ReadConfig().get_devices_ip())
        devices = get_devices()
        print('\nThere has %s  devices alive in config IP list' % len(devices))

    elif method == 'USB':
        # get  devices connected PC with USB
        print('Get available USB devices connected on PC... ')
        devices = connect_devices()
        print('\nThere has %s  USB devices alive ' % len(devices))

    else:
        raise Exception('Config.ini method illegal:method =%s' % method)

    return devices


class Drivers:
    @staticmethod
    def _run_cases(run, cases):
        log = Log()
        log.set_logger(run.get_device()['model'], os.path.join(run.get_path(), 'client.log'))
        log.i('udid: %s' % run.get_device()['udid'])

        # set cls.path, it must be call before operate on any page
        path = ReportPath()
        path.set_path(run.get_path())

        # set cls.driver, it must be call before operate on any page
        base_page = BasePage()
        if 'ip' in run.get_device():
            base_page.set_driver(run.get_device()['ip'])
        else:
            base_page.set_driver(run.get_device()['serial'])

        try:
            # run cases
            base_page.set_fastinput_ime()
            base_page.d.shell('logcat -c')  # 清空logcat

            run.run(cases)

            # 将logcat文件上传到报告
            base_page.d.shell('logcat -d > /sdcard/logcat.log')
            time.sleep(1)
            base_page.d.pull('/sdcard/logcat.log', os.path.join(path.get_path(), 'logcat.log'))

            base_page.set_original_ime()
            base_page.identify()
            if ReadConfig().get_method().strip() in ["UDID", "SERVER2"]:
                log.i('release device %s ' % run.get_device()['serial'])
                atxserver2(ReadConfig().get_server_url()).release_device(run.get_device()['serial'])
            else:
                pass
        except AssertionError as e:
            log.e('AssertionError, %s', e)



    @staticmethod
    def _run_maxim(run, cases, command, actions, widget_black):
        log = Log()
        log.set_logger(run.get_device()['model'], os.path.join(run.get_path(), 'client.log'))
        log.i('udid: %s', run.get_device()['udid'])

        # set cls.path, it must be call before operate on any page
        path = ReportPath()
        path.set_path(run.get_path())

        # set cls.driver, it must be call before operate on any page
        base_page = BasePage()
        if 'ip' in run.get_device():
            base_page.set_driver(run.get_device()['ip'])
        else:
            base_page.set_driver(run.get_device()['serial'])

        try:
            # run cases
            base_page.d.shell('logcat -c')  # 清空logcat
            if cases:
                run.run_cases(cases)
            Maxim().run_monkey(monkey_shell=command, actions=actions, widget_black=widget_black)

            base_page.d.shell('logcat -d > /sdcard/logcat.log')
            time.sleep(1)
            base_page.d.pull('/sdcard/logcat.log', os.path.join(path.get_path(), 'logcat.log'))
            base_page.d.pull('/sdcard/monkeyerr.txt', os.path.join(path.get_path(), 'monkeyerr.txt'))
            base_page.d.pull('/sdcard/monkeyout.txt', os.path.join(path.get_path(), 'monkeyout.txt'))

            base_page.set_original_ime()
            base_page.identify()
            if ReadConfig().get_method().strip() in ["UDID", "SERVER2"]:
                log.i('release device %s ' % run.get_device()['serial'])
                atxserver2(ReadConfig().get_server_url()).release_device(run.get_device()['serial'])
            else:
                pass
        except AssertionError as e:
            log.e('AssertionError, %s', e)

    def run(self, cases):
        start_time = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        devices = check_devives()
        if not devices:
            print('There is no device found,test over.')
            return

        # generate test data data.json 准备测试数据
        generate_test_data(devices)

        print('Starting Run test >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        runs = []
        for i in range(len(devices)):
            runs.append(RunCases(devices[i]))
        # run on every device 开始执行测试
        pool = Pool(processes=len(runs))
        for run in runs:
            pool.apply_async(self._run_cases,
                             args=(run, cases,))
        print('Waiting for all runs done........ ')
        pool.close()
        pool.join()
        print('All runs done........ ')
        ChromeDriver.kill()

        #  Generate statistics report  生成统计测试报告 将所有设备的报告在一个HTML中展示
        create_statistics_report(runs)
        backup_report('./TestReport', './TestReport_History', start_time)


    def run_maxim(self, cases=None, command=None, actions=False, widget_black=False):
        start_time = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        devices = check_devives()
        if not devices:
            print('There is no device found,test over.')
            return
        print('Starting Run test >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')

        runs = []
        for i in range(len(devices)):
            runs.append(RunMaxim(devices[i]))

        # run on every device 开始执行测试
        pool = Pool(processes=len(runs))
        for run in runs:
            pool.apply_async(self._run_maxim,
                             args=(run, cases, command, actions, widget_black,))
        print('Waiting for all runs done........ ')
        pool.close()
        pool.join()
        print('All runs done........ ')
        backup_report('./MaximReport', './MaximReport_History', start_time)




# if __name__ == '__main__':
#     if ReadConfig().get_method().strip() in ["UDID", "SERVER2"]:
#         atxserver2(ReadConfig().get_server_url()).release_device('ce051715b2ef600802')
#     else:
#         pass
