# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2018 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, 51 Franklin Street, Fifth Floor, Boston, MA 02110-1335, USA.
#
# Authors:
#     Valerio Cosentino <valcos@bitergia.com>
#

import logging
import os

from graal.graal import (Graal,
                         GraalCommand,
                         GraalError,
                         DEFAULT_WORKTREE_PATH)
from graal.backends.core.analyzers.reverse import Reverse
from perceval.backend import BackendCommandArgumentParser
from perceval.utils import DEFAULT_DATETIME, DEFAULT_LAST_DATETIME
from grimoirelab.toolkit.datetime import str_to_datetime

CATEGORY_CODEP = 'code_dependencies'

logger = logging.getLogger(__name__)


class CoDep(Graal):
    """CoDep backend.

    This class extends the Graal backend. It extract package and class dependencies
    of a Python module to understand its evolution.

    :param uri: URI of the Git repository
    :param gitpath: path to the repository or to the log file
    :param worktreepath: the directory where to store the working tree
    :param tag: label used to mark the data
    :param archive: archive to store/retrieve items

    :raises RepositoryError: raised when there was an error cloning or
        updating the repository.
    """
    version = '0.1.0'

    CATEGORIES = [CATEGORY_CODEP]

    def __init__(self, uri, git_path, worktreepath=DEFAULT_WORKTREE_PATH,
                 tag=None, archive=None):
        super().__init__(uri, git_path, worktreepath, tag=tag, archive=archive)

        self.dependency_analyzer = DependencyAnalyzer()
        self.monthly_checkpoints = []

    def fetch(self, category=CATEGORY_CODEP, paths=None,
              from_date=DEFAULT_DATETIME, to_date=DEFAULT_LAST_DATETIME,
              branches=None, latest_items=False):
        """Fetch commits and code (package and class) dependencies information."""

        items = super().fetch(category, paths=paths,
                              from_date=from_date, to_date=to_date,
                              branches=branches, latest_items=latest_items)

        return items

    @staticmethod
    def metadata_category(item):
        """Extracts the category from a Code item.

        This backend only generates one type of item which is
        'code_dependencies'.
        """
        return CATEGORY_CODEP

    def _filter_commit(self, commit, ncommit, paths=None):
        """Filter a commit according to its data (e.g., author, sha, etc.)

        :param commit: a Perceval commit item
        :param ncommit: commit number (from the initial commit)
        :param paths: a list of paths to drive the filtering

        :returns: a boolean value
        """
        authored_date = str_to_datetime(commit['AuthorDate'])

        checkpoint = '-'.join([str(authored_date.year), str(authored_date.month)])

        if checkpoint in self.monthly_checkpoints:
            return True

        self.monthly_checkpoints.append(checkpoint)
        return False

    def _analyze(self, commit, paths=None):
        """Analyse a snapshot and the corresponding
        checkout version of the repository

        :param commit: a Perceval commit item
        :param paths: a list of paths to narrow the analysis
        """
        if not paths:
            raise GraalError(cause="paths cannot be null")

        if len(paths) > 1:
            logger.warning("Only the first path will be analyzed")

        module_path = os.path.join(self.worktreepath, paths[0])

        if not os.path.exists(module_path):
            logger.warning("module path %s does not exist at commit %s, analysis will be skipped"
                           % (module_path, commit['commit']))
            return {}

        analysis = self.dependency_analyzer.analyze(module_path)
        return analysis

    def _post(self, commit):
        """Remove attributes of the Graal item obtained

        :param commit: a Graal commit item
        """
        commit.pop('Author', None)
        commit.pop('Commit', None)
        commit.pop('files', None)
        commit.pop('parents', None)
        commit.pop('refs', None)
        return commit


class DependencyAnalyzer:
    """Class to obtain a graph representation of package and class dependencies information
    from a Python module. Such a representation can be then used to plot an UML diagram using common
    visualization libraries.
    """

    def __init__(self):
        self.reverse = Reverse()

    def analyze(self, module_path):
        """Analyze the content of a Python project using Pyreverse

        :param module_path: folder path

        :returns a dict containing the results of the analysis, like the one below
        {
          'image_path': ..
        }
        """
        kwargs = {'module_path': module_path}
        analysis = self.reverse.analyze(**kwargs)

        return analysis


class CoDepCommand(GraalCommand):
    """Class to run CoDep backend from the command line."""

    BACKEND = CoDep
