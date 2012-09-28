ROUTES = (
    ('dev.index', ''),
    ('dev.system', 's/{system_id:\d+}'),
    ('dev.parameter', 'p/{parameter_id:\d+}'),

    (
        'sngconnect.api.system_parameter',
        'api/v1/feeds/{system_id:\d+}/datastreams/{parameter_id:\d+}.json'
    ),
)
