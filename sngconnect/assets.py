from webassets import Bundle

ASSET_BUNDLES = {
    'base_css': Bundle(
        'wuxia/css/sngconnect.css',
        filters=('cssrewrite', 'cssmin',),
        output='compressed/base.css'
    ),
    'base_js': Bundle(
        'wuxia/js/libs/jquery.js',
        'wuxia/js/libs/modernizr.js',
        'wuxia/js/libs/selectivizr.js',
        'wuxia/js/bootstrap/bootstrap-affix.js',
        'wuxia/js/navigation.js',
        'wuxia/js/bootstrap/bootstrap-dropdown.js',
        'wuxia/js/bootstrap/bootstrap-alert.js',
        'wuxia/js/bootstrap/bootstrap-modal.js',
        'wuxia/js/bootstrap/bootstrap-tooltip.js',
        'wuxia/js/plugins/datepicker/bootstrap-datepicker.js',
        'iso8601/iso8601.js',
        'highcharts/js/highcharts.js',
        'sngconnect/js/base.js',
        filters='rjsmin',
        output='compressed/base.js'
    ),
}
