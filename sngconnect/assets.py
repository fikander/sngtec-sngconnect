from webassets import Bundle

# TODO: add 'less' as 1st filter (once puppet system config is fixed)
#       use 'wuxia/less/style.less' instead of 'wuxia/css/sngconnect.css'
CSS_FILTERS = ('cssrewrite', 'yui_css',)
JS_FILTERS = 'yui_js'

ASSET_BUNDLES = {
    'base_css': Bundle(
        'wuxia/css/sngconnect.css',
        filters=CSS_FILTERS,
        output='compressed/base.css'
    ),
    'base_js': Bundle(
        'justgage/js/raphael.2.1.0.js',
        'justgage/js/justgage.1.0.1.js',
        'wuxia/js/libs/jquery.js',
        'wuxia/js/libs/modernizr.js',
        'wuxia/js/libs/selectivizr.js',
        'wuxia/js/bootstrap/bootstrap-affix.js',
        'wuxia/js/navigation.js',
        'wuxia/js/bootstrap/bootstrap-dropdown.js',
        'wuxia/js/bootstrap/bootstrap-alert.js',
        'wuxia/js/bootstrap/bootstrap-modal.js',
        'wuxia/js/bootstrap/bootstrap-tooltip.js',
        'wuxia/js/bootstrap/bootstrap-rowlink.js',
        'highcharts/js/highcharts.js',
        'iso8601/iso8601.js',
        'wuxia/js/plugins/datepicker/bootstrap-datepicker.js',
        'sngconnect/js/base.js',
        filters=JS_FILTERS,
        output='compressed/base.js'
    ),
    'appearance_css': Bundle(
        'codemirror/lib/codemirror.css',
        filters=CSS_FILTERS,
        output='compressed/appearance.css'
    ),
    'appearance_js': Bundle(
        'codemirror/lib/codemirror.js',
        'codemirror/mode/css/css.js',
        filters=JS_FILTERS,
        output='compressed/appearance.js'
    ),
}
