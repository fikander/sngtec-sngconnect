ROUTES = (
    # sngconnect.telemetry
    ('sngconnect.telemetry.dashboard', ''),
    ('sngconnect.telemetry.feeds', 'feeds'),
    (
        'sngconnect.telemetry.feed_dashboard',
        'feeds/{feed_id:\d+}'
    ),
    (
        'sngconnect.telemetry.feed_charts',
        'feeds/{feed_id:\d+}/charts'
    ),
    (
        'sngconnect.telemetry.feed_data_streams',
        'feeds/{feed_id:\d+}/data_streams'
    ),
    (
        'sngconnect.telemetry.feed_data_stream',
        'feeds/{feed_id:\d+}/data_streams/{data_stream_id:\d+}'
    ),
    (
        'sngconnect.telemetry.feed_settings',
        'feeds/{feed_id:\d+}/settings'
    ),
    (
        'sngconnect.telemetry.feed_setting',
        'feeds/{feed_id:\d+}/settings/{data_stream_id:\d+}'
    ),
    (
        'sngconnect.telemetry.feed_history',
        'feeds/{feed_id:\d+}/history'
    ),
    # sngconnect.accounts
    ('sngconnect.accounts.sign_in', 'accounts/sign_in'),
    ('sngconnect.accounts.sign_out', 'accounts/sign_out'),
    # sngconnect.api
    (
        'sngconnect.api.feed_data_stream',
        'api/v1/feeds/{feed_id:\d+}/datastreams/{data_stream_id:\d+}.json'
    ),
    (
        'sngconnect.api.feed',
        'api/v1/feeds/{feed_id:\d+}.json'
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
)
