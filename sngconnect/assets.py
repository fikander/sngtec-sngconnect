from webassets import Bundle

CSS_FILTERS = ('cssrewrite', 'yui_css',)
JS_FILTERS = 'yui_js'

ASSET_BUNDLES = {
    'base_css': Bundle(
        'wuxia/css/sngconnect.css',
        filters=CSS_FILTERS,
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
