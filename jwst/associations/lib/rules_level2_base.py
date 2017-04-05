"""Base classes which define the Level2 Associations"""
import logging
from os.path import basename
import re

from jwst.associations import (
    Association,
    libpath
)
from jwst.associations.lib.dms_base import DMSBaseMixin
from jwst.associations.lib.rules_level3_base import _EMPTY
from jwst.associations.lib.rules_level3_base import Utility as Utility_Level3

# Configure logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

__all__ = [
    'ASN_SCHEMA',
    'AsnMixin_Lv2Image',
    'AsnMixin_Lv2Mode',
    'AsnMixin_Lv2Spec',
    'DMSLevel2bBase',
    'Utility'
]

# The schema that these associations must adhere to.
ASN_SCHEMA = libpath('asn_schema_jw_level2b.json')

# File templates
_DMS_POOLNAME_REGEX = 'jw(\d{5})_(\d{3})_(\d{8}[Tt]\d{6})_pool'
_LEVEL1B_REGEX = '(?P<path>.+)(?P<type>_uncal)(?P<extension>\..+)'


class DMSLevel2bBase(DMSBaseMixin, Association):
    """Basic class for DMS Level2 associations."""

    # Set the validation schema
    schema_file = ASN_SCHEMA

    # Attribute values that are indicate the
    # attribute is not specified.
    INVALID_VALUES = _EMPTY

    def __init__(self, *args, **kwargs):

        # I am defined by the following constraints
        self.add_constraints({
            'program': {
                'value': None,
                'inputs': ['PROGRAM']
            },
            'n_members': {
                'test': self.match_constraint,
                'value': '0',
                'inputs': lambda: str(len(self.data.get('members', [])))
            }
        })

        # Now, lets see if member belongs to us.
        super(DMSLevel2bBase, self).__init__(*args, **kwargs)

    def match_member_count(self, member, constraint, conditions):
        """
        Test for number of members currently in the association
        Parameters
        ----------
        member: dict
            The member to retrieve the values from

        constraint: str
            The name of the constraint

        conditions: dict
            The conditions structure

        Raises
        ------
        AssociationError
            If the match fails

        AssociationProcessMembers
            If more members need to be reprocessed.
        """

    def __eq__(self, other):
        """Compare equality of two assocaitions"""
        if isinstance(other, DMSLevel2bBase):
            result = self.data['asn_type'] == other.data['asn_type']
            result = result and (self.data['members'] == other.data['members'])
            return result
        else:
            return NotImplemented

    def __ne__(self, other):
        """Compare inequality of two associations"""
        if isinstance(other, DMSLevel2bBase):
            return not self.__eq__(other)
        else:
            return NotImplemented

    def _init_hook(self, member):
        """Post-check and pre-add initialization"""
        self.data['target'] = member['TARGETID']
        self.data['program'] = str(member['PROGRAM'])
        self.data['asn_pool'] = basename(
            member.meta['pool_file']
        ).split('.')[0]
        self.data['constraints'] = '\n'.join(
            [cc for cc in self.constraints_to_text()]
        )
        self.data['asn_id'] = self.acid.id
        self.data['members'] = []

    def _add(self, member):
        """Add member to this association."""
        entry = {
            'expname': Utility.rename_to_level2a(member['FILENAME']),
            'exptype': Utility.get_exposure_type(member, default='SCIENCE')
        }
        self.data['members'].append(entry)

    def __repr__(self):
        try:
            file_name, json_repr = self.ioregistry['json'].dump(self)
        except:
            return str(self.__class__)
        return json_repr

    def __str__(self):
        """Create human readable version of the association
        """

        result = ['Association {:s}'.format(self.asn_name)]

        # Parameters of the association
        result.append('    Parameters:')
        result.append('        Product type: {:s}'.format(self.data['asn_type']))
        result.append('        Rule:         {:s}'.format(self.data['asn_rule']))
        result.append('        Program:      {:s}'.format(self.data['program']))
        result.append('        Target:       {:s}'.format(self.data['target']))
        result.append('        Pool:         {:s}'.format(self.data['asn_pool']))

        for cc in self.constraints_to_text():
            result.append('        {:s}'.format(cc))

        # Products of the assocation
        result.append('\n    Members:')
        for member in self.data['members']:
                result.append('        {:s}: {:s}'.format(
                    member['expname'], member['exptype'])
                )

        # That's all folks
        result.append('\n')
        return '\n'.join(result)


class Utility(object):
    """Utility functions that understand DMS Level 3 associations"""

    @staticmethod
    def rename_to_level2a(level1b_name):
        """Rename a Level 1b Exposure to another level

        Parameters
        ----------
        level1b_name: str
            The Level 1b exposure name.

        Returns
        -------
        str
            The Level 2a name
        """
        match = re.match(_LEVEL1B_REGEX, level1b_name)
        if match is None or match.group('type') != '_uncal':
            logger.warn((
                'Member FILENAME="{}" is not a Level 1b name. '
                'Cannot transform to Level 2a.'
            ).format(
                level1b_name
            ))
            return level1b_name

        level2a_name = ''.join([
            match.group('path'),
            '_rate',
            match.group('extension')
        ])
        return level2a_name

    @staticmethod
    def get_exposure_type(*args, **kwargs):
        return Utility_Level3.get_exposure_type(*args, **kwargs)

    @staticmethod
    def resequence(*args, **kwargs):
        return Utility_Level3.resequence(*args, **kwargs)


# ---------------------------------------------
# Mixins to define the broad category of rules.
# ---------------------------------------------
class AsnMixin_Lv2Image(DMSLevel2bBase):
    """Level 2 Image association base"""

    def __init__(self, *args, **kwargs):

        self.add_constraints({
            'exp_type': {
                'value': 'NRC_IMAGE|MIR_IMAGE|NIS_IMAGE|FGS_IMAGE',
                'inputs': ['EXP_TYPE'],
                'force_unique': True,
            }
        })

        super(AsnMixin_Lv2Image, self).__init__(*args, **kwargs)

    def _init_hook(self, member):
        """Post-check and pre-add initialization"""

        super(AsnMixin_Lv2Image, self)._init_hook(member)
        self.data['asn_type'] = 'image2'


class AsnMixin_Lv2Spec(DMSLevel2bBase):
    """Level 2 Spectral association base"""

    def __init__(self, *args, **kwargs):

        self.add_constraints({
            'exp_type': {
                'value': (
                    'NRC_GRISM'
                    '|NRC_TSGRISM'
                    '|MIR_LRS-FIXEDSLIT'
                    '|MIR_LRS-SLITLESS'
                    '|NRS_FIXEDSLIT'
                    '|NRS_IFU'
                    '|NRS_MSASPEC'
                    '|NRS_BRIGHTOBJ'
                    '|NIS_WFSS'
                    '|NIS_SOSS'
                ),
                'inputs': ['EXP_TYPE'],
                'force_unique': True,
            }
        })

        super(AsnMixin_Lv2Spec, self).__init__(*args, **kwargs)

    def _init_hook(self, member):
        """Post-check and pre-add initialization"""

        super(AsnMixin_Lv2Spec, self)._init_hook(member)
        self.data['asn_type'] = 'spec2'


class AsnMixin_Lv2Mode(DMSLevel2bBase):
    """Fix the instrument configuration"""
    def __init__(self, *args, **kwargs):

        # I am defined by the following constraints
        self.add_constraints({
            'program': {
                'value': None,
                'inputs': ['PROGRAM']
            },
            'instrument': {
                'value': None,
                'inputs': ['INSTRUME']
            },
            'detector': {
                'value': None,
                'inputs': ['DETECTOR']
            },
            'opt_elem': {
                'value': None,
                'inputs': ['FILTER']
            },
            'opt_elem2': {
                'value': None,
                'inputs': ['PUPIL', 'GRATING'],
                'required': False,
            },
            'subarray': {
                'value': None,
                'inputs': ['SUBARRAY'],
                'required': False,
            },
            'channel': {
                'value': None,
                'inputs': ['CHANNEL'],
                'required': False,
            }
        })

        super(AsnMixin_Lv2Mode, self).__init__(*args, **kwargs)
