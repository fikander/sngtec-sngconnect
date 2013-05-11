ROUTES = (
    # sngconnect.telemetry
    (
        'sngconnect.telemetry.dashboard',
        ''
    ),
    (
        'sngconnect.telemetry.feeds',
        'feeds'
    ),
    (
        'sngconnect.telemetry.feeds.new',
        'feeds/new'
    ),
    (
        'sngconnect.telemetry.feed_dashboard',
        'feeds/{feed_id:\d+}'
    ),
    (
        'sngconnect.telemetry.feed_dashboard.set_value',
        'feeds/{feed_id:\d+}/set-value/{data_stream_template_id:\d+}'
    ),
    (
        'sngconnect.telemetry.feed_charts',
        'feeds/{feed_id:\d+}/charts'
    ),
    (
        'sngconnect.telemetry.feed_charts.create',
        'feeds/{feed_id:\d+}/charts/create'
    ),
    (
        'sngconnect.telemetry.feed_chart',
        'feeds/{feed_id:\d+}/charts/{chart_definition_id:\d+}'
    ),
    (
        'sngconnect.telemetry.feed_chart.data',
        'feeds/{feed_id:\d+}/charts/{chart_definition_id:\d+}/data'
    ),
    (
        'sngconnect.telemetry.feed_chart.update',
        'feeds/{feed_id:\d+}/charts/{chart_definition_id:\d+}/update'
    ),
    (
        'sngconnect.telemetry.feed_chart.delete',
        'feeds/{feed_id:\d+}/charts/{chart_definition_id:\d+}/delete'
    ),
    (
        'sngconnect.telemetry.feed_data_streams',
        'feeds/{feed_id:\d+}/parameters'
    ),
    (
        'sngconnect.telemetry.feed_data_stream',
        'feeds/{feed_id:\d+}/parameters/{data_stream_label:\w+}'
    ),
    (
        'sngconnect.telemetry.feed_data_stream.chart_data',
        'feeds/{feed_id:\d+}/parameters/{data_stream_label:\w+}/data'
    ),
    (
        'sngconnect.telemetry.feed_settings',
        'feeds/{feed_id:\d+}/settings'
    ),
    (
        'sngconnect.telemetry.feed_setting',
        'feeds/{feed_id:\d+}/settings/{data_stream_label:\w+}'
    ),
    (
        'sngconnect.telemetry.feed_permissions',
        'feeds/{feed_id:\d+}/permissions'
    ),
    (
        'sngconnect.telemetry.feed_permissions.set_user_permissions',
        'feeds/{feed_id:\d+}/permissions/set-user-permissions'
    ),
    (
        'sngconnect.telemetry.feed_permissions.revoke_maintainer_access',
        'feeds/{feed_id:\d+}/permissions/remove-maintainer-access'
    ),
    (
        'sngconnect.telemetry.feed_history',
        'feeds/{feed_id:\d+}/history'
    ),
    (
        'sngconnect.telemetry.confirm_message',
        'feeds/confirm-message'
    ),
    # sngconnect.payments
    (
        'sngconnect.payments.index',
        'payments/'
    ),
    (
        'sngconnect.payments.confirmation',
        'payments/confirmation'
    ),
    (
        'sngconnect.payments.calculate_price',
        'payments/calculate_price'
    ),
    # sngconnect.payments.payu
    (
        'sngconnect.payments.payu.notify',
        'payments/payu/notify'
    ),
    # sngconnect.devices
    (
        'sngconnect.devices.feed_templates',
        'devices/'
    ),
    (
        'sngconnect.devices.feed_template',
        'devices/{feed_template_id:\d+}'
    ),
    (
        'sngconnect.devices.feed_template_delete',
        'devices/{feed_template_id:\d+}/delete'
    ),
    (
        'sngconnect.devices.data_stream_template',
        'devices/{feed_template_id:\d+}/parameters'
            '/{data_stream_template_id:\d+}'
    ),
    (
        'sngconnect.devices.data_stream_template_delete',
        'devices/{feed_template_id:\d+}/parameters'
            '/{data_stream_template_id:\d+}/delete'
    ),
    (
        'sngconnect.devices.chart_definition',
        'devices/{feed_template_id:\d+}/charts/{chart_definition_id:\d+}'
    ),
    (
        'sngconnect.devices.chart_definition_delete',
        'devices/{feed_template_id:\d+}/charts'
            '/{chart_definition_id:\d+}/delete',
    ),
    # sngconnect.appearance
    (
        'sngconnect.appearance.appearance',
        'appearance/'
    ),
    (
        'sngconnect.appearance.delete_asset',
        'appearance/delete-asset/'
    ),
    # sngconnect.announcements
    (
        'sngconnect.announcements.announcements',
        'announcements/'
    ),
    # sngconnect.accounts
    (
        'sngconnect.accounts.sign_in',
        'accounts/sign_in'
    ),
    (
        'sngconnect.accounts.sign_out',
        'accounts/sign_out'
    ),
    (
        'sngconnect.accounts.sign_up',
        'accounts/sign_up'
    ),
    (
        'sngconnect.accounts.settings',
        'accounts/settings'
    ),
    (
        'sngconnect.accounts.activate',
        'accounts/activate/{email:[^/]+}/{email_activation_code:\w+}'
    ),
    # sngconnect.api
    (
        'sngconnect.api.feed_data_stream',
        'api/v1/feeds/{feed_id:\d+}/datastreams/{data_stream_label:\w+}.json'
    ),
    (
        'sngconnect.api.feed',
        'api/v1/feeds/{feed_id:\d+}/datastreams.json'
    ),
    (
        'sngconnect.api.events',
        'api/v1/feeds/{feed_id:\d+}/events.json'
    ),
    (
        'sngconnect.api.commands',
        'api/v1/feeds/{feed_id:\d+}/commands.json'
    ),
    (
        'sngconnect.api.upload_log',
        'api/v1/upload-log/{log_request_id:\d+}/{log_request_hash:\w+}.json'
    ),
    (
        'sngconnect.api.feed_configuration',
        'api/v1/feeds/{feed_id:\d+}/configuration.json'
    ),
    (
        'sngconnect.api.activate',
        'api/v1/activate/{feed_id:\d+}'
    ),
)
