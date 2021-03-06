# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""Tests for `aiida.engine.processes.workchains.restart` module."""
# pylint: disable=invalid-name,inconsistent-return-statements,no-self-use,no-member
import pytest

from aiida.engine import CalcJob, BaseRestartWorkChain, process_handler, ProcessState, ProcessHandlerReport, ExitCode


class SomeWorkChain(BaseRestartWorkChain):
    """Dummy class."""

    _process_class = CalcJob

    @process_handler(priority=200)
    def handler_a(self, node):
        if node.exit_status == 400:
            return ProcessHandlerReport(do_break=False, exit_code=ExitCode(418, 'IMATEAPOT'))

    @process_handler(priority=100)
    def handler_b(self, _):
        return

    def not_a_handler(self, _):
        pass


def test_is_process_handler():
    """Test the `BaseRestartWorkChain.is_process_handler` class method."""
    assert SomeWorkChain.is_process_handler('handler_a')
    assert not SomeWorkChain.is_process_handler('not_a_handler')
    assert not SomeWorkChain.is_process_handler('unexisting_method')


def test_get_process_handler():
    """Test the `BaseRestartWorkChain.get_process_handlers` class method."""
    assert [handler.__name__ for handler in SomeWorkChain.get_process_handlers()] == ['handler_a', 'handler_b']


@pytest.mark.usefixtures('clear_database_before_test')
def test_excepted_process(generate_work_chain, generate_calculation_node):
    """Test that the workchain aborts if the sub process was excepted."""
    process = generate_work_chain(SomeWorkChain, {})
    process.setup()
    process.ctx.children = [generate_calculation_node(ProcessState.EXCEPTED)]
    assert process.inspect_process() == BaseRestartWorkChain.exit_codes.ERROR_SUB_PROCESS_EXCEPTED


@pytest.mark.usefixtures('clear_database_before_test')
def test_killed_process(generate_work_chain, generate_calculation_node):
    """Test that the workchain aborts if the sub process was killed."""
    process = generate_work_chain(SomeWorkChain, {})
    process.setup()
    process.ctx.children = [generate_calculation_node(ProcessState.KILLED)]
    assert process.inspect_process() == BaseRestartWorkChain.exit_codes.ERROR_SUB_PROCESS_KILLED


@pytest.mark.usefixtures('clear_database_before_test')
def test_unhandled_failure(generate_work_chain, generate_calculation_node):
    """Test the unhandled failure mechanism.

    The workchain should be aborted if there are two consecutive failed sub processes that went unhandled. We simulate
    it by setting `ctx.unhandled_failure` to True and append two failed process nodes in `ctx.children`.
    """
    process = generate_work_chain(SomeWorkChain, {})
    process.setup()
    process.ctx.children = [generate_calculation_node(exit_status=100)]
    assert process.inspect_process() is None
    assert process.ctx.unhandled_failure is True

    process.ctx.children.append(generate_calculation_node(exit_status=100))
    assert process.inspect_process() == BaseRestartWorkChain.exit_codes.ERROR_SECOND_CONSECUTIVE_UNHANDLED_FAILURE  # pylint: disable=no-member


@pytest.mark.usefixtures('clear_database_before_test')
def test_unhandled_reset_after_success(generate_work_chain, generate_calculation_node):
    """Test `ctx.unhandled_failure` is reset to `False` in `inspect_process` after a successful process."""
    process = generate_work_chain(SomeWorkChain, {})
    process.setup()
    process.ctx.children = [generate_calculation_node(exit_status=100)]
    assert process.inspect_process() is None
    assert process.ctx.unhandled_failure is True

    process.ctx.children.append(generate_calculation_node(exit_status=0))
    assert process.inspect_process() is None
    assert process.ctx.unhandled_failure is False


@pytest.mark.usefixtures('clear_database_before_test')
def test_unhandled_reset_after_handled(generate_work_chain, generate_calculation_node):
    """Test `ctx.unhandled_failure` is reset to `False` in `inspect_process` after a handled failed process."""
    process = generate_work_chain(SomeWorkChain, {})
    process.setup()
    process.ctx.children = [generate_calculation_node(exit_status=300)]
    assert process.inspect_process() is None
    assert process.ctx.unhandled_failure is True

    # Exit status 400 of the last calculation job will be handled and so should reset the flag
    process.ctx.children.append(generate_calculation_node(exit_status=400))
    result = process.inspect_process()

    # Even though `handler_a` was followed by `handler_b`, we should retrieve the exit_code from `handler_a` because
    # `handler_b` returned `None` which should not overwrite the last report.
    assert isinstance(result, ExitCode)
    assert result.status == 418
    assert result.message == 'IMATEAPOT'
    assert process.ctx.unhandled_failure is False
