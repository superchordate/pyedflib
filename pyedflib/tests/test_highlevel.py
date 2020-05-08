# -*- coding: utf-8 -*-
# Copyright (c) 2015 Holger Nahrstaedt
from __future__ import division, print_function, absolute_import

import os, sys
import numpy as np
# from numpy.testing import (assert_raises, run_module_suite,
#                            assert_equal, assert_allclose, assert_almost_equal)
import unittest
from pyedflib import highlevel
from datetime import datetime, date

class TestHighLevel(unittest.TestCase):
    
    def setUp(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.edfplus_data_file = os.path.join(data_dir, 'tmp_test_file_plus.edf')
        self.test_generator = os.path.join(data_dir, 'test_generator.edf')
        self.test_accented = os.path.join(data_dir, u"test_áä'üöß.edf")
        self.anonymized = os.path.join(data_dir, u"anonymized.edf")
        self.personalized = os.path.join(data_dir, u"personalized.edf")
        self.drop_from = os.path.join(data_dir, 'drop_from.edf')
        
        
    def test_dig2phys_calc(self):
        signals_phys, shead, _ = highlevel.read_edf(self.test_generator)
        signals_dig, _, _ = highlevel.read_edf(self.test_generator, digital=True)
                
        dmin, dmax = shead[0]['digital_min'],  shead[0]['digital_max']
        pmin, pmax = shead[0]['physical_min'],  shead[0]['physical_max']
        
        # convert to physical
        signal_phys2 = highlevel.dig2phys(signals_dig, dmin, dmax, pmin, pmax)        
        np.testing.assert_allclose(signals_phys, signal_phys2)
        
        # convert to digital
        signals_dig2 = highlevel.phys2dig(signals_phys, dmin, dmax, pmin, pmax)
        signals_dig2 = np.rint(signals_dig2)
        np.testing.assert_allclose(signals_dig, signals_dig2)

    def test_read_write_edf(self):
        startdate = datetime.now()
        t = startdate
        startdate = datetime(t.year,t.month,t.day,t.hour, t.minute,t.second)
        
        header = highlevel.make_header(technician='tech', recording_additional='radd',
                                                patientname='name', patient_additional='padd',
                                                patientcode='42', equipment='eeg', admincode='420',
                                                gender='Male', startdate=startdate,birthdate='05.09.1980')
        annotations = [[0.01, -1, 'begin'],[0.5, -1, 'middle'],[10, -1, 'end']]
        header['annotations'] = annotations
        signal_headers1 = highlevel.make_signal_headers(['ch'+str(i) for i in range(5)])
        signals = np.random.rand(5, 256*300)*200 #5 minutes of eeg
        
        success = highlevel.write_edf(self.edfplus_data_file, signals, signal_headers1, header)
        self.assertTrue(os.path.isfile(self.edfplus_data_file))
        self.assertGreater(os.path.getsize(self.edfplus_data_file), 0)
        self.assertTrue(success)
        
        signals2, signal_headers2, header2 = highlevel.read_edf(self.edfplus_data_file)

        self.assertEqual(len(signals2), 5)
        self.assertEqual(len(signals2), len(signal_headers2))
        for shead1, shead2 in zip(signal_headers1, signal_headers2):
            self.assertDictEqual(shead1, shead2)
            
        self.assertDictEqual(header, header2)
        np.testing.assert_allclose(signals, signals2, atol=0.01)
    
        signals = (signals*100).astype(np.int8)
        success = highlevel.write_edf(self.edfplus_data_file, signals,  signal_headers1, header, digital=True)
        self.assertTrue(os.path.isfile(self.edfplus_data_file))
        self.assertGreater(os.path.getsize(self.edfplus_data_file), 0)
        self.assertTrue(success)
        
        signals2, signal_headers2, header2 = highlevel.read_edf(self.edfplus_data_file, digital=True)

        self.assertEqual(len(signals2), 5)
        self.assertEqual(len(signals2), len(signal_headers2))
        for shead1, shead2 in zip(signal_headers1, signal_headers2):
            self.assertDictEqual(shead1, shead2)
            
        self.assertDictEqual(header, header2)
        np.testing.assert_array_equal(signals, signals2)
        
        
    def test_read_write_with_annotations(self):
        signals, signal_headers, header = highlevel.read_edf(self.test_generator)
        expected = [[0.0, -1, 'Recording starts'], [600.0, -1, 'Recording ends']]
        self.assertEqual(header['annotations'], expected)
        
        highlevel.write_edf(self.edfplus_data_file, signals, signal_headers, header)
        signals2, signal_header2s, header2 = highlevel.read_edf(self.edfplus_data_file)
        self.assertEqual(header['annotations'], header2['annotations'])

        
    def test_quick_write(self):
        signals = np.random.randint(-2048, 2048, [3, 256*60])
        highlevel.write_edf_quick(self.edfplus_data_file, signals.astype(np.int32), sfreq=256, digital=True)
        signals2, _, _ = highlevel.read_edf(self.edfplus_data_file, digital=True)
        np.testing.assert_allclose(signals, signals2)
        signals = np.random.rand(3, 256*60)
        highlevel.write_edf_quick(self.edfplus_data_file, signals, sfreq=256)
        signals2, _, _ = highlevel.read_edf(self.edfplus_data_file)
        np.testing.assert_allclose(signals, signals2, atol=0.00002)
        
    def test_read_write_diff_sfreq(self):
        
        signals = []
        sfreqs = [1, 64, 128, 200]
        sheaders = []
        for sfreq in sfreqs:
            signals.append(np.random.randint(-2048, 2048, sfreq*60).astype(np.int32))
            shead = highlevel.make_signal_header('ch{}'.format(sfreq), sample_rate=sfreq)
            sheaders.append(shead)
        highlevel.write_edf(self.edfplus_data_file, signals, sheaders, digital=True)
        signals2, sheaders2, _ = highlevel.read_edf(self.edfplus_data_file, digital=True)
        for s1, s2 in zip(signals, signals2):
            np.testing.assert_allclose(s1, s2)
        
    def test_assertion_dmindmax(self):
        
        # test digital and dmin wrong
        signals =[np.random.randint(-2048, 2048, 256*60).astype(np.int32)]
        sheaders = [highlevel.make_signal_header('ch1', sample_rate=256)]
        sheaders[0]['digital_min'] = -128
        sheaders[0]['digital_max'] = 128
        with self.assertRaises(AssertionError):
            highlevel.write_edf(self.edfplus_data_file, signals, sheaders, digital=True)
        
        # test pmin wrong
        signals = [np.random.randint(-2048, 2048, 256*60)]
        sheaders = [highlevel.make_signal_header('ch1', sample_rate=256)]
        sheaders[0]['physical_min'] = -200
        sheaders[0]['physical_max'] = 200
        with self.assertRaises(AssertionError):
            highlevel.write_edf(self.edfplus_data_file, signals, sheaders, digital=False)
            

    def test_read_write_accented(self):
        signals = np.random.rand(3, 256*60)
        highlevel.write_edf_quick(self.test_accented, signals, sfreq=256)
        assert os.path.isfile(self.test_accented), '{} does not exist'.format(self.test_accented)
        signals2, _, _ = highlevel.read_edf(self.test_accented)
        
        np.testing.assert_allclose(signals, signals2, atol=0.00002)
            
        
    def test_read_header(self):
        
        header = highlevel.read_edf_header(self.test_generator)
        self.assertEqual(len(header), 14)
        self.assertEqual(len(header['channels']), 11)
        self.assertEqual(len(header['SignalHeaders']), 11)
        self.assertEqual(header['Duration'], 600)
        self.assertEqual(header['admincode'], 'Dr. X')
        self.assertEqual(header['birthdate'], '30 jun 1969')
        self.assertEqual(header['equipment'], 'test generator')
        self.assertEqual(header['gender'], 'Male')
        self.assertEqual(header['patient_additional'], 'patient')
        self.assertEqual(header['patientcode'], 'abcxyz99')
        self.assertEqual(header['patientname'], 'Hans Muller')
        self.assertEqual(header['technician'], 'Mr. Spotty')
        
        
    def test_anonymize(self):
        
        header = highlevel.make_header(technician='tech', recording_additional='radd',
                                                patientname='name', patient_additional='padd',
                                                patientcode='42', equipment='eeg', admincode='420',
                                                gender='Male', birthdate='05.09.1980')
        annotations = [[0.01, -1, 'begin'],[0.5, -1, 'middle'],[10, -1, 'end']]
        header['annotations'] = annotations
        signal_headers = highlevel.make_signal_headers(['ch'+str(i) for i in range(3)])
        signals = np.random.rand(3, 256*300)*200 #5 minutes of eeg
        highlevel.write_edf(self.personalized, signals, signal_headers, header)
    
        
    
        highlevel.anonymize_edf(self.personalized, new_file=self.anonymized,
                                        to_remove=['patientname', 'birthdate',
                                                   'admincode', 'patientcode',
                                                   'technician'],
                                        new_values=['x', '', 'xx', 'xxx',
                                                    'xxxx'], verify=True)
        new_header = highlevel.read_edf_header(self.anonymized)
        self.assertEqual(new_header['birthdate'], '')
        self.assertEqual(new_header['patientname'], 'x')
        self.assertEqual(new_header['admincode'], 'xx')
        self.assertEqual(new_header['patientcode'], 'xxx')
        self.assertEqual(new_header['technician'], 'xxxx')


        highlevel.anonymize_edf(self.personalized, to_remove=['patientname', 'birthdate',
                                                   'admincode', 'patientcode',
                                                   'technician'],
                                        new_values=['x', '', 'xx', 'xxx',
                                                    'xxxx'], verify=True)
        new_header = highlevel.read_edf_header(self.personalized[:-4]+'_anonymized.edf')
        self.assertEqual(new_header['birthdate'], '')
        self.assertEqual(new_header['patientname'], 'x')
        self.assertEqual(new_header['admincode'], 'xx')
        self.assertEqual(new_header['patientcode'], 'xxx')
        self.assertEqual(new_header['technician'], 'xxxx')

        with self.assertRaises(AssertionError):
            highlevel.anonymize_edf(self.personalized, 
                                    new_file=self.anonymized,
                                    to_remove=['patientname', 'birthdate',
                                               'admincode', 'patientcode',
                                               'technician'],
                                    new_values=['x', '', 'xx', 'xxx'],
                                    verify=True)
            
    def test_drop_channel(self):
        signal_headers = highlevel.make_signal_headers(['ch'+str(i) for i in range(5)])
        signals = np.random.rand(5, 256*300)*200 #5 minutes of eeg
        highlevel.write_edf(self.drop_from, signals, signal_headers)
        
        dropped = highlevel.drop_channels(self.drop_from, to_keep=['ch1', 'ch2'])
        
        signals2, signal_headers, header = highlevel.read_edf(dropped)
        
        np.testing.assert_allclose(signals[1:3,:], signals2, atol=0.01)
        
        highlevel.drop_channels(self.drop_from, self.drop_from[:-4]+'2.edf',
                                to_drop=['ch0', 'ch1', 'ch2'])
        signals2, signal_headers, header = highlevel.read_edf(self.drop_from[:-4]+'2.edf')

        np.testing.assert_allclose(signals[3:,:], signals2, atol=0.01)
        
        with self.assertRaises(AssertionError):
            highlevel.drop_channels(self.drop_from, to_keep=['ch1'], to_drop=['ch3'])


    # def test_rename_channels(self):
        # raise NotImplementedError


if __name__ == '__main__':
    # run_module_suite(argv=sys.argv)
    unittest.main()
