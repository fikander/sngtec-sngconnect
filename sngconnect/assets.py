from webassets import Bundle

ASSET_BUNDLES = {
    'base_css': Bundle(
        'wuxia/css/wuxia-red.css',
        'sngconnect/css/base.css',
        filters=('cssrewrite', 'cssmin',),
        output='compressed/base.css'
    ),
    'base_js': Bundle(
        'wuxia/js/libs/jquery.js',
        'wuxia/js/libs/modernizr.js',
        'wuxia/js/libs/selectivizr.js',
        'wuxia/js/bootstrap/bootstrap-dropdown.js',
        'sngconnect/js/base.js',
        filters='rjsmin',
        output='compressed/base.js'
    ),
}
