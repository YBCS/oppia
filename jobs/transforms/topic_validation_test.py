# coding: utf-8
#
# Copyright 2021 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for jobs.transforms.topic_validation."""

from __future__ import absolute_import  # pylint: disable=import-only-modules
from __future__ import unicode_literals  # pylint: disable=import-only-modules

import datetime

from core.platform import models
from jobs import job_test_utils
from jobs.transforms import topic_validation
from jobs.types import base_validation_errors
from jobs.types import topic_validation_errors

import apache_beam as beam

(base_models, topic_models) = models.Registry.import_models(
    [models.NAMES.base_model, models.NAMES.topic])


class ValidateCanonicalNameMatchesNameInLowercaseTests(
        job_test_utils.PipelinedTestBase):

    NOW = datetime.datetime.utcnow()

    def test_process_for_not_matching_canonical_name(self):
        model_with_different_name = topic_models.TopicModel(
            id='123',
            name='name',
            created_on=self.NOW,
            last_updated=self.NOW,
            url_fragment='name-two',
            canonical_name='canonical_name',
            next_subtopic_id=1,
            language_code='en',
            subtopic_schema_version=0,
            story_reference_schema_version=0
        )
        output = (
            self.pipeline
            | beam.Create([model_with_different_name])
            | beam.ParDo(
                topic_validation.ValidateCanonicalNameMatchesNameInLowercase())
        )
        self.assert_pcoll_equal(output, [
            topic_validation_errors.ModelCanonicalNameMismatchError(
                model_with_different_name)
        ])

    def test_process_for_matching_canonical_name(self):
        model_with_same_name = topic_models.TopicModel(
            id='123',
            name='SOMEthing',
            created_on=self.NOW,
            last_updated=self.NOW,
            url_fragment='name-two',
            canonical_name='something',
            next_subtopic_id=1,
            language_code='en',
            subtopic_schema_version=0,
            story_reference_schema_version=0
        )
        output = (
            self.pipeline
            | beam.Create([model_with_same_name])
            | beam.ParDo(
                topic_validation.ValidateCanonicalNameMatchesNameInLowercase())
        )
        self.assert_pcoll_equal(output, [])


class ValidateTopicCommitCmdsSchemaTests(job_test_utils.PipelinedTestBase):

    def test_validate_change_domain_implemented(self):
        invalid_commit_cmd_model = topic_models.TopicCommitLogEntryModel(
            id='123',
            created_on=self.YEAR_AGO,
            last_updated=self.NOW,
            commit_type='test-type',
            user_id='',
            topic_id='123',
            post_commit_status='private',
            commit_cmds=[{
                'cmd': base_models.VersionedModel.CMD_DELETE_COMMIT}])

        output = (
            self.pipeline
            | beam.Create([invalid_commit_cmd_model])
            | beam.ParDo(
                topic_validation.ValidateTopicCommitCmdsSchema())
        )

        self.assert_pcoll_equal(output, [])

    def test_topic_change_object_with_missing_cmd(self):
        invalid_commit_cmd_model = topic_models.TopicCommitLogEntryModel(
            id='123',
            created_on=self.YEAR_AGO,
            last_updated=self.NOW,
            commit_type='test-type',
            user_id='',
            topic_id='123',
            post_commit_status='private',
            commit_cmds=[{'invalid': 'data'}])

        output = (
            self.pipeline
            | beam.Create([invalid_commit_cmd_model])
            | beam.ParDo(
                topic_validation.ValidateTopicCommitCmdsSchema())
        )

        self.assert_pcoll_equal(output, [
            base_validation_errors.CommitCmdsValidateError(
                invalid_commit_cmd_model,
                {'invalid': 'data'},
                'Missing cmd key in change dict')
        ])

    def test_topic_change_object_with_invalid_cmd(self):
        invalid_commit_cmd_model = topic_models.TopicCommitLogEntryModel(
            id='123',
            created_on=self.YEAR_AGO,
            last_updated=self.NOW,
            commit_type='test-type',
            user_id='',
            topic_id='123',
            post_commit_status='private',
            commit_cmds=[{'cmd': 'invalid'}])

        output = (
            self.pipeline
            | beam.Create([invalid_commit_cmd_model])
            | beam.ParDo(
                topic_validation.ValidateTopicCommitCmdsSchema())
        )

        self.assert_pcoll_equal(output, [
            base_validation_errors.CommitCmdsValidateError(
                invalid_commit_cmd_model,
                {'cmd': 'invalid'},
                'Command invalid is not allowed')
        ])

    def test_topic_change_object_with_missing_attribute_in_cmd(self):
        invalid_commit_cmd_model = topic_models.TopicCommitLogEntryModel(
            id='123',
            created_on=self.YEAR_AGO,
            last_updated=self.NOW,
            commit_type='test-type',
            user_id='',
            topic_id='123',
            post_commit_status='private',
            commit_cmds=[{
                'cmd': 'update_topic_property',
                'property_name': 'name',
            }])

        output = (
            self.pipeline
            | beam.Create([invalid_commit_cmd_model])
            | beam.ParDo(
                topic_validation.ValidateTopicCommitCmdsSchema())
        )

        self.assert_pcoll_equal(output, [
            base_validation_errors.CommitCmdsValidateError(
                invalid_commit_cmd_model,
                {
                    'cmd': 'update_topic_property',
                    'property_name': 'name',
                },
                'The following required attributes are missing: '
                'new_value, old_value')
        ])

    def test_topic_change_object_with_extra_attribute_in_cmd(self):
        invalid_commit_cmd_model = topic_models.TopicCommitLogEntryModel(
            id='123',
            created_on=self.YEAR_AGO,
            last_updated=self.NOW,
            commit_type='test-type',
            user_id='',
            topic_id='123',
            post_commit_status='private',
            commit_cmds=[{
                'cmd': 'add_subtopic',
                'title': 'title',
                'subtopic_id': 'subtopic_id',
                'invalid': 'invalid'
            }])

        output = (
            self.pipeline
            | beam.Create([invalid_commit_cmd_model])
            | beam.ParDo(
                topic_validation.ValidateTopicCommitCmdsSchema())
        )

        self.assert_pcoll_equal(output, [
            base_validation_errors.CommitCmdsValidateError(
                invalid_commit_cmd_model,
                {
                    'cmd': 'add_subtopic',
                    'title': 'title',
                    'subtopic_id': 'subtopic_id',
                    'invalid': 'invalid'
                },
                'The following extra attributes are present: invalid')
        ])

    def test_topic_change_object_with_invalid_topic_property(self):
        invalid_commit_cmd_model = topic_models.TopicSnapshotMetadataModel(
            id='123',
            created_on=self.YEAR_AGO,
            last_updated=self.NOW,
            committer_id='committer_id',
            commit_type='create',
            commit_cmds_user_ids=[
                'commit_cmds_user_1_id', 'commit_cmds_user_2_id'],
            content_user_ids=['content_user_1_id', 'content_user_2_id'],
            commit_cmds=[{
                'cmd': 'update_topic_property',
                'property_name': 'invalid',
                'old_value': 'old_value',
                'new_value': 'new_value',
            }])

        output = (
            self.pipeline
            | beam.Create([invalid_commit_cmd_model])
            | beam.ParDo(
                topic_validation.ValidateTopicCommitCmdsSchema())
        )

        self.assert_pcoll_equal(output, [
            base_validation_errors.CommitCmdsValidateError(
                invalid_commit_cmd_model,
                {
                    'cmd': 'update_topic_property',
                    'property_name': 'invalid',
                    'old_value': 'old_value',
                    'new_value': 'new_value',
                },
                'Value for property_name in cmd update_topic_property: '
                'invalid is not allowed')
        ])

    def test_topic_change_object_with_invalid_subtopic_property(self):
        invalid_commit_cmd_model = topic_models.TopicSnapshotMetadataModel(
            id='123',
            created_on=self.YEAR_AGO,
            last_updated=self.NOW,
            committer_id='committer_id',
            commit_type='create',
            commit_cmds_user_ids=[
                'commit_cmds_user_1_id', 'commit_cmds_user_2_id'],
            content_user_ids=['content_user_1_id', 'content_user_2_id'],
            commit_cmds=[{
                'cmd': 'update_subtopic_property',
                'subtopic_id': 'subtopic_id',
                'property_name': 'invalid',
                'old_value': 'old_value',
                'new_value': 'new_value',
            }])

        output = (
            self.pipeline
            | beam.Create([invalid_commit_cmd_model])
            | beam.ParDo(
                topic_validation.ValidateTopicCommitCmdsSchema())
        )

        self.assert_pcoll_equal(output, [
            base_validation_errors.CommitCmdsValidateError(
                invalid_commit_cmd_model,
                {
                    'cmd': 'update_subtopic_property',
                    'subtopic_id': 'subtopic_id',
                    'property_name': 'invalid',
                    'old_value': 'old_value',
                    'new_value': 'new_value',
                },
                'Value for property_name in cmd update_subtopic_property: '
                'invalid is not allowed')
        ])

    def test_topic_change_object_with_invalid_subtopic_page_property(self):
        invalid_commit_cmd_model = topic_models.TopicSnapshotMetadataModel(
            id='123',
            created_on=self.YEAR_AGO,
            last_updated=self.NOW,
            committer_id='committer_id',
            commit_type='create',
            commit_cmds_user_ids=[
                'commit_cmds_user_1_id', 'commit_cmds_user_2_id'],
            content_user_ids=['content_user_1_id', 'content_user_2_id'],
            commit_cmds=[{
                'cmd': 'update_subtopic_page_property',
                'subtopic_id': 'subtopic_id',
                'property_name': 'invalid',
                'old_value': 'old_value',
                'new_value': 'new_value',
            }])

        output = (
            self.pipeline
            | beam.Create([invalid_commit_cmd_model])
            | beam.ParDo(
                topic_validation.ValidateTopicCommitCmdsSchema())
        )

        self.assert_pcoll_equal(output, [
            base_validation_errors.CommitCmdsValidateError(
                invalid_commit_cmd_model,
                {
                    'cmd': 'update_subtopic_page_property',
                    'subtopic_id': 'subtopic_id',
                    'property_name': 'invalid',
                    'old_value': 'old_value',
                    'new_value': 'new_value',
                },
                'Value for property_name in cmd update_subtopic_page_property: '
                'invalid is not allowed')
        ])
