#!/usr/bin/env python3 -X utf8
import json
import os
import tempfile

import pytest
import requests

from fuzzer import Fuzzer


class TestClass(object):

    @classmethod
    def setup_class(cls):
        """
        Setup test class at initialization
        """
        cls.report_dir = tempfile.mkdtemp()
        cls.report_files = list()
        cls.test_app_url = "http://127.0.0.1:5000/"
        print('Setup_class with report dir: {}'.format(cls.report_dir))
        with open('./test_swagger_definition.json', 'r') as f:
            cls.swagger = json.loads(f.read())

    def teardown_method(self, method):
        """
        Clears the report directory at the end of each test run
        :param method: test method
        """
        print('Removing {} report files...'.format(len(self.report_files)))
        for f in self.report_files:
            filepath = '{}/{}'.format(self.report_dir, f)
            os.remove(filepath)

    def query_last_call(self):
        """
        Queries the test application and gets the details of the last call which sent by the fuzzer
        :return: dict
        """
        _resp = requests.get('{}{}'.format(self.test_app_url, 'last_call'), timeout=1)
        assert _resp.status_code == 200, 'Response headers: {}, response body: {}'.format(_resp.headers, _resp.content)
        return json.loads(_resp.content.decode("utf-8"))

    def fuzz(self, api_resources):
        """
        Call APIFuzzer with the given api definition
        :type api_resources: dict
        """
        with pytest.raises(SystemExit):
            prog = Fuzzer(api_resources=api_resources,
                          report_dir=self.report_dir,
                          test_level=1,
                          alternate_url=self.test_app_url,
                          test_result_dst=None,
                          log_level='Debug',
                          auth_headers={}
                          )
            prog.prepare()
            prog.run()

    def get_last_report_file(self):
        self.report_files = os.listdir(self.report_dir)
        with open("{}/{}".format(self.report_dir, self.report_files[0]), mode='r', encoding='utf-8') as f:
            return json.loads(f.read())

    def test_integer_status_code(self):
        api_endpoint_to_test = self.swagger['paths']['/exception/{integer_id}']
        print('API to test: {}'.format(api_endpoint_to_test))
        self.swagger.pop('paths')
        self.swagger['paths'] = {}
        self.swagger['paths']['/exception/{integer_id}'] = api_endpoint_to_test
        self.fuzz(self.swagger)
        last_call = self.query_last_call()
        # last_call field:
        # "req_path": "/exception/\u001f/\u001c\u007f\u0000N@",
        last_value_sent = last_call['req_path'].replace('/exception/', '')
        assert not isinstance(last_value_sent, int), last_value_sent
        assert last_call['resp_status'] == 500, last_call['resp_status'] + "Received"
        # report file test
        required_report_fields = ['status', 'sub_reports', 'name', 'request_body', 'request_headers', 'state',
                                  'request_method', 'reason', 'request_url', 'response', 'test_number']
        last_report = self.get_last_report_file()
        assert_msg = json.dumps(last_report, sort_keys=True, indent=2)
        for field in required_report_fields:
            assert field in last_report.keys(), assert_msg
        if last_report.get('parsed_status_code') is not None:
            assert last_report['parsed_status_code'] == 500, assert_msg
