ROUTES = (
    # sngconnect.telemetry
    ('sngconnect.telemetry.dashboard', ''),
    ('sngconnect.telemetry.systems', 'systems'),
    (
        'sngconnect.telemetry.system_dashboard',
        'systems/{system_id:\d+}'
    ),
    (
        'sngconnect.telemetry.system_charts',
        'systems/{system_id:\d+}/charts'
    ),
    (
        'sngconnect.telemetry.system_parameters',
        'systems/{system_id:\d+}/parameters'
    ),
    (
        'sngconnect.telemetry.system_parameter',
        'systems/{system_id:\d+}/parameters/{parameter_id:\d+}'
    ),
    (
        'sngconnect.telemetry.system_settings',
        'systems/{system_id:\d+}/settings'
    ),
    (
        'sngconnect.telemetry.system_setting',
        'systems/{system_id:\d+}/settings/{parameter_id:\d+}'
    ),
    (
        'sngconnect.telemetry.system_history',
        'systems/{system_id:\d+}/history'
    ),
    # sngconnect.accounts
    ('sngconnect.accounts.sign_in', 'accounts/sign_in'),
    ('sngconnect.accounts.sign_out', 'accounts/sign_out'),
    # sngconnect.api
    (
        'sngconnect.api.system_parameter',
        'api/v1/feeds/{system_id:\d+}/datastreams/{parameter_id:\d+}.json'
    ),
    (
        'sngconnect.api.system',
        'api/v1/feeds/{system_id:\d+}.json'
    ),
    (
        'sngconnect.api.events',
        'api/v1/feeds/{system_id:\d+}/events.json'
    ),
)
