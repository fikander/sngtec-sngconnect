# -*- coding: utf-8 -*-

import datetime
import decimal
import json

import isodate
import pytz
import sqlalchemy as sql
from sqlalchemy.orm import exc as database_exceptions
from pyramid.response import Response
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.database import (DBSession, Feed, DataStream, ChartDefinition,
    FeedTemplate)
from sngconnect.cassandra import data_streams as data_streams_store
from sngconnect.telemetry import forms, schemas
from sngconnect.telemetry.views.feed.base import FeedViewBase

@view_config(
    route_name='sngconnect.telemetry.feed_charts',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/charts.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedCharts(FeedViewBase):
    def __init__(self, request):
        super(FeedCharts, self).__init__(request)
        if 'access_charts' not in self.feed_permissions:
            raise httpexceptions.HTTPUnauthorized()
        self.chart_definitions = DBSession.query(ChartDefinition).join(
            FeedTemplate,
            Feed
        ).filter(
            sql.or_(
                FeedTemplate.id == self.feed.template_id,
                Feed.id == self.feed.id
            )
        ).order_by(
            ChartDefinition.feed_id,
            ChartDefinition.name
        ).all()
        self.context.update({
            'chart_definitions': [
                {
                    'id': chart_definition.id,
                    'name': chart_definition.name,
                    'description': chart_definition.description,
                    'editable': chart_definition.feed is not None,
                    'change_url': request.route_url(
                        'sngconnect.telemetry.feed_chart.update',
                        feed_id=self.feed.id,
                        chart_definition_id=chart_definition.id
                    ),
                    'change_form': forms.UpdateChartDefinitionForm(
                        chart_definition.id,
                        self.feed,
                        self.feed.template.data_stream_templates,
                        obj=chart_definition,
                        csrf_context=self.request
                    ),
                    'delete_url': request.route_url(
                        'sngconnect.telemetry.feed_chart.delete',
                        feed_id=self.feed.id,
                        chart_definition_id=chart_definition.id
                    ),
                    'delete_form': forms.DeleteChartDefinitionForm(
                        csrf_context=self.request
                    ),
                    'url': self.request.route_url(
                        'sngconnect.telemetry.feed_chart',
                        feed_id=self.feed.id,
                        chart_definition_id=chart_definition.id
                    ),
                }
                for chart_definition in self.chart_definitions
            ],
            'create_chart_url': self.request.route_url(
                'sngconnect.telemetry.feed_charts.create',
                feed_id=self.feed.id
            ),
            'create_chart_form': {
                'LINEAR': forms.CreateChartDefinitionForm(
                    self.feed,
                    self.feed.template.data_stream_templates,
                    chart_type='LINEAR',
                    csrf_context=self.request
                ),
                'DIFFERENTIAL': forms.CreateChartDefinitionForm(
                    self.feed,
                    self.feed.template.data_stream_templates,
                    chart_type='DIFFERENTIAL',
                    csrf_context=self.request
                ),
            },
            'chart': None,
        })

@view_config(
    route_name='sngconnect.telemetry.feed_charts.create',
    request_method='POST',
    permission='sngconnect.telemetry.access'
)
class FeedChartsCreate(FeedViewBase):
    def __call__(self):
        if 'access_charts' not in self.feed_permissions:
            raise httpexceptions.HTTPUnauthorized()
        create_chart_form = forms.CreateChartDefinitionForm(
            self.feed,
            self.feed.template.data_stream_templates,
            csrf_context=self.request
        )
        create_chart_form.process(self.request.POST)
        data_stream_templates_dict = dict((
            (template.id, template)
            for template in self.feed.template.data_stream_templates
        ))
        if create_chart_form.validate():
            chart_definition = ChartDefinition(
                feed_template=self.feed.template,
                feed=self.feed
            )
            create_chart_form.populate_obj(chart_definition)
            for id in create_chart_form.data_stream_template_ids.data:
                chart_definition.data_stream_templates.append(
                    data_stream_templates_dict[id]
                )
            DBSession.add(chart_definition)
            return Response(
                json.dumps({
                    'redirect': None,
                }),
                content_type='application/json'
            )
        return Response(
            json.dumps({
                'errors': create_chart_form.errors,
            }),
            content_type='application/json'
        )

@view_config(
    route_name='sngconnect.telemetry.feed_chart',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/chart.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedChart(FeedCharts):
    def __call__(self):
        try:
            chart_definition = filter(
                lambda cd: (
                    cd.id == int(self.request.matchdict['chart_definition_id'])
                ),
                self.chart_definitions
            )[0]
        except (ValueError, IndexError):
            raise httpexceptions.HTTPNotFound()
        self.context['chart'] = {
            'definition': {
                'id': chart_definition.id,
                'name': chart_definition.name,
            },
            'rendering_data': {
                'id': chart_definition.id,
                'name': chart_definition.name,
                'type': chart_definition.chart_type,
                'data_url': self.request.route_url(
                    'sngconnect.telemetry.feed_chart.data',
                    feed_id=self.feed.id,
                    chart_definition_id=chart_definition.id
                ),
                'data_stream_templates': [
                    {
                        'id': template.id,
                        'name': template.name,
                        'measurement_unit': template.measurement_unit,
                        'minimum': template.default_minimum,
                        'maximum': template.default_maximum,
                    }
                    for template in sorted(
                        chart_definition.data_stream_templates,
                        None,
                        lambda template: template.id
                    )
                ],
            },
        }
        self.context['set_range_form'] = forms.SetChartRangeForm(
            start=datetime.date.today() - datetime.timedelta(days=1),
            end=datetime.date.today(),
            csrf_context=self.request
        )
        return self.context

class FeedChartDefinitionViewBase(FeedViewBase):
    def __init__(self, request):
        super(FeedChartDefinitionViewBase, self).__init__(request)
        try:
            self.chart_definition = DBSession.query(ChartDefinition).filter(
                (ChartDefinition.id ==
                    self.request.matchdict['chart_definition_id']),
                ChartDefinition.feed_template_id == self.feed.template_id
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
        # charts on the dashboard are visible for evey user, so never block access
        if (not self.chart_definition.show_on_dashboard and
                'access_charts' not in self.feed_permissions):
            raise httpexceptions.HTTPUnauthorized()


class ChartDataMixin(object):
    def __call__(self):
        try:
            last = max(0, int(self.request.GET['last']))
        except (KeyError, ValueError):
            last = None
        try:
            end = isodate.parse_datetime(self.request.GET['end'])
        except (KeyError, isodate.ISO8601Error):
            end = None
        try:
            start = isodate.parse_datetime(self.request.GET['start'])
        except (KeyError, isodate.ISO8601Error):
            start = None
        if end is None:
            end = pytz.utc.localize(datetime.datetime.utcnow())
        if start is None:
            if last is None:
                start = end - datetime.timedelta(hours=24)
            else:
                start = end - datetime.timedelta(hours=last)
        data_stream_template_ids = map(
            lambda dst: dst.id,
            self.data_stream_templates
        )
        data_stream_ids = DBSession.query(DataStream.id).filter(
            DataStream.feed == self.feed,
            DataStream.template_id.in_(data_stream_template_ids)
        ).order_by(
            DataStream.template_id
        )
        series_appstruct = []
        if start is not None and last is not None:
            delta = datetime.timedelta(hours=last)
        else:
            delta = end - start
        aggregate = True
        if (self.chart_type != 'DIFFERENTIAL' and
                delta <= datetime.timedelta(hours=24)):
            data_store = data_streams_store.Measurements()
            aggregate = False
        elif delta <= datetime.timedelta(days=35):
            data_store = data_streams_store.HourlyAggregates()
        else:
            data_store = data_streams_store.DailyAggregates()
        for data_stream_id in map(lambda x: x.id, data_stream_ids):
            data_points = data_store.get_data_points(
                data_stream_id,
                start_date=start,
                end_date=end
            )
            if aggregate:
                if self.chart_type == 'DIFFERENTIAL':
                    data_points = map(
                        lambda dp: (
                            dp[0],
                            decimal.Decimal(dp[1]['minimum'])
                        ),
                        data_points
                    )
                else:
                    data_points = map(
                        lambda dp: (
                            dp[0],
                            (
                                decimal.Decimal(dp[1]['sum']) /
                                    decimal.Decimal(dp[1]['count'])
                            ).quantize(decimal.Decimal('.01'))
                        ),
                        data_points
                    )
            else:
                data_points = map(
                    lambda dp: (
                        dp[0],
                        decimal.Decimal(dp[1])
                    ),
                    data_points
                )
            if self.chart_type == 'DIFFERENTIAL':
                differential_data_points = []
                for i in range(len(data_points)):
                    try:
                        differential_data_points.append((
                            data_points[i][0],
                            data_points[i + 1][1] - data_points[i][1]
                        ))
                    except IndexError:
                        break
                data_points = differential_data_points
            series_appstruct.append(
                data_points
            )
        return Response(
            json.dumps(schemas.ChartDataResponse().serialize(series_appstruct)),
            content_type='application/json'
        )

@view_config(
    route_name='sngconnect.telemetry.feed_chart.data',
    request_method='GET',
    permission='sngconnect.telemetry.access'
)
class FeedChartData(ChartDataMixin, FeedChartDefinitionViewBase):

    def __init__(self, request):
        super(FeedChartData, self).__init__(request)
        self.data_stream_templates = (
            self.chart_definition.data_stream_templates
        )
        self.chart_type = self.chart_definition.chart_type

@view_config(
    route_name='sngconnect.telemetry.feed_chart.update',
    request_method='POST',
    permission='sngconnect.telemetry.access'
)
class FeedChartsUpdate(FeedChartDefinitionViewBase):
    def __call__(self):
        update_chart_form = forms.UpdateChartDefinitionForm(
            self.chart_definition.id,
            self.feed,
            self.feed.template.data_stream_templates,
            csrf_context=self.request
        )
        update_chart_form.process(self.request.POST)
        data_stream_templates_dict = dict((
            (template.id, template)
            for template in self.feed.template.data_stream_templates
        ))
        if update_chart_form.validate():
            update_chart_form.populate_obj(self.chart_definition)
            self.chart_definition.data_stream_templates = []
            for id in update_chart_form.data_stream_template_ids.data:
                self.chart_definition.data_stream_templates.append(
                    data_stream_templates_dict[id]
                )
            DBSession.add(self.chart_definition)
            return Response(
                json.dumps({
                    'redirect': None,
                }),
                content_type='application/json'
            )
        return Response(
            json.dumps({
                'errors': update_chart_form.errors,
            }),
            content_type='application/json'
        )

@view_config(
    route_name='sngconnect.telemetry.feed_chart.delete',
    request_method='POST',
    permission='sngconnect.telemetry.access'
)
class FeedChartsDelete(FeedChartDefinitionViewBase):
    def __call__(self):
        delete_chart_form = forms.DeleteChartDefinitionForm(
            csrf_context=self.request
        )
        delete_chart_form.process(self.request.POST)
        if delete_chart_form.validate():
            DBSession.delete(self.chart_definition)
            return Response(
                json.dumps({
                    'redirect': self.request.route_url(
                        'sngconnect.telemetry.feed_charts',
                        feed_id=self.feed.id
                    ),
                }),
                content_type='application/json'
            )
        return Response(status_code=400)
