from pathlib import Path

import pytest

from helperFunctions.config import get_config_for_testing
from helperFunctions.tag import TagColor
from objects.file import FileObject
from ..code.elf_analysis import AnalysisPlugin

TEST_DATA_DIR = Path(Path(__file__).parent, 'data')


class MockAdmin:
    def register_plugin(self, name, administrator):
        pass


@pytest.fixture(scope='function')
def test_config():
    return get_config_for_testing()


@pytest.fixture(scope='function')
def stub_object():
    test_object = FileObject(file_path=str(Path(TEST_DATA_DIR, 'test_binary')))
    test_object.processed_analysis['file_type'] = {'mime': 'application/x-executable'}

    return test_object


@pytest.fixture(scope='function')
def stub_plugin(test_config, monkeypatch):
    monkeypatch.setattr('plugins.base.BasePlugin._sync_view', lambda self, plugin_path: None)
    return AnalysisPlugin(MockAdmin(), test_config, offline_testing=True)


def test_process_analysis(stub_plugin, stub_object):
    stub_object.processed_analysis['file_type'] = {'mime': 'application/x-executable'}
    stub_plugin.process_object(stub_object)

    assert stub_object.processed_analysis[stub_plugin.PLUGIN_NAME]['Output'] != {}
    assert sorted(stub_object.processed_analysis[stub_plugin.PLUGIN_NAME]['summary']) == ['dynamic_entries', 'exported_functions', 'header', 'imported_functions', 'sections', 'segments']


@pytest.mark.parametrize('tag, tag_color', [
    ('crypto', TagColor.RED),
    ('file_system', TagColor.BLUE),
    ('network', TagColor.ORANGE),
    ('memory_operations', TagColor.GREEN),
    ('randomize', TagColor.LIGHT_BLUE),
    ('other', TagColor.GRAY)])
def test_get_color_code(stub_plugin, tag, tag_color):
    assert stub_plugin._get_color_codes(tag) == tag_color


testdata = [
    (['a'], 'b', ['c'], [], []),
    (['a', 'b', 'c'], 'b', ['c'], [], ['b']),
    (['a', 'b', 'c'], 'b', ['c'], ['b'], ['b', 'b']),
    (['a', 'b', 'c'], 'b', ['c', 'a'], [], ['b', 'b']),
    (['a', 'b', 'c'], 'b', ['d', 'e'], [], []),
    (['a', 'b', 'c'], 'b', ['d', 'e'], ['x'], ['x'])
]


@pytest.mark.parametrize('json_items,  key, library_list, tag_list, expected', testdata)
def test_get_tags_from_library_list(stub_plugin, json_items,  key, library_list, tag_list, expected):
    assert stub_plugin._get_tags_from_library_list(json_items,  key, library_list, tag_list) == expected


testdata = [
    (['GLIBC_2.3.4(4)', '* Local *', 'GLIBC_2.2.5(3)', '* Global *', 'GLIBC_2.2.5(3)'],
     ['GLIBC_2.3.4', 'GLIBC_2.2.5'])

]


@pytest.mark.parametrize('symbol_versions, expected', testdata)
def test_get_symbols_version_entries(stub_plugin, symbol_versions, expected):
    assert sorted(stub_plugin._get_symbols_version_entries(symbol_versions)) == sorted(expected)
