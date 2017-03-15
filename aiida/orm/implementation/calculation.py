# -*- coding: utf-8 -*-

from __future__ import absolute_import

from aiida.backends.settings import BACKEND
from aiida.common.exceptions import ConfigurationError
from aiida.backends.profile import BACKEND_DJANGO, BACKEND_SQLA

from aiida.common.pluginloader import from_type_to_pluginclassname
from aiida.orm.implementation.general.calculation.job import _input_subfolder


if BACKEND == BACKEND_SQLA:
    from aiida.orm.implementation.sqlalchemy.calculation import Calculation
    from aiida.orm.implementation.sqlalchemy.calculation.job import JobCalculation
    from aiida.orm.implementation.sqlalchemy.calculation.inline import (
        InlineCalculation, make_inline)

elif BACKEND == BACKEND_DJANGO:
    from aiida.orm.implementation.django.calculation import Calculation
    from aiida.orm.implementation.django.calculation.job import JobCalculation
    from aiida.orm.implementation.django.calculation.inline import (
        InlineCalculation, make_inline)

else:
    raise ConfigurationError("Invalid settings.BACKEND: {}".format(
                BACKEND))

