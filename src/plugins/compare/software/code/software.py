from __future__ import annotations

from typing import TYPE_CHECKING

from compare.PluginBase import CompareBasePlugin
from helperFunctions.compare_sets import iter_element_and_rest

if TYPE_CHECKING:
    from objects.file import FileObject


class ComparePlugin(CompareBasePlugin):
    """
    Compares Software
    """

    NAME = 'Software'
    DEPENDENCIES = ['software_components']  # noqa: RUF012
    FILE = __file__

    def compare_function(self, fo_list, dependency_results: dict[str, dict]):  # noqa: ARG002
        compare_result = {
            'software_in_common': self._get_intersection_of_software(fo_list),
            'exclusive_software': self._get_exclusive_software(fo_list),
        }
        if len(fo_list) > 2:  # noqa: PLR2004
            compare_result[
                'software_in_more_than_one_but_not_in_all'
            ] = self._get_software_in_more_than_one_but_not_in_all(fo_list, compare_result)
        return compare_result

    def _get_exclusive_software(self, fo_list: list[FileObject]) -> dict:
        result = {'collapse': True}
        for current_element, other_elements in iter_element_and_rest(fo_list):
            result[current_element.uid] = list(
                set.difference(
                    self._get_software_set(current_element), *[self._get_software_set(fo) for fo in other_elements]
                )
            )
        return result

    def _get_intersection_of_software(self, fo_list):
        intersecting_software = set.intersection(*[self._get_software_set(fo) for fo in fo_list])
        return {'all': list(intersecting_software), 'collapse': True}

    def _get_software_in_more_than_one_but_not_in_all(self, fo_list, result_dict):
        result = {'collapse': True}
        for current_element in fo_list:
            result[current_element.uid] = list(
                set.difference(
                    self._get_software_set(current_element),
                    result_dict['software_in_common']['all'],
                    result_dict['exclusive_software'][current_element.uid],
                )
            )
        return result

    @staticmethod
    def _get_software_set(fo: FileObject) -> set[str]:
        return set(fo.processed_analysis['software_components']['summary'].keys())
