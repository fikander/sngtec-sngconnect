ROUTES = (
    # sngconnect.telemetry
    ('sngconnect.telemetry.dashboard', ''),
    (
        'sngconnect.telemetry.system_dashboard',
        'system/{system_id:\d+}'
    ),
    (
        'sngconnect.telemetry.system_charts',
        'system/{system_id:\d+}/charts'
    ),
    (
        'sngconnect.telemetry.system_parameters',
        'system/{system_id:\d+}/parameters'
    ),
    (
        'sngconnect.telemetry.parameter',
        'system/{system_id:\d+}/parameters/{parameter_id:\d+}'
    ),
    (
        'sngconnect.telemetry.system_settings',
        'system/{system_id:\d+}/settings'
    ),
    (
        'sngconnect.telemetry.setting',
        'system/{system_id:\d+}/settings/{parameter_id:\d+}'
    ),
    (
        'sngconnect.telemetry.system_history',
        'system/{system_id:\d+}/history'
    ),
    # sngconnect.accounts
    ('sngconnect.accounts.sign_in', 'accounts/sign_in'),
    ('sngconnect.accounts.sign_out', 'accounts/sign_out'),
    # sngconnect.api
    (
        'sngconnect.api.system_parameter',
        'api/v1/feeds/{system_id:\d+}/datastreams/{parameter_id:\d+}.json'
    ),
)
