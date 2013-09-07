import os

from pyramid.response import Response
from pyramid.view import view_config

# _here = /app/location/myapp

_here = os.path.dirname(__file__)

# _icon = /app/location/myapp/static/favicon.ico

_icon = open(os.path.join(
			_here, 'static', 'favicon.ico')).read()
_fi_response = Response(content_type='image/x-icon',
						body=_icon)

# _robots = /app/location/myapp/static/robots.txt

_robots = open(os.path.join(
			   _here, 'static', 'robots.txt')).read()
_robots_response = Response(content_type='text/plain',
							body=_robots)

# _apple_touch = /app/location/myapp/static/apple-touch-icon.png

_apple_touch = open(os.path.join(
				_here, 'static', 'apple-touch-icon.png')).read()
_apple_touch_response = Response(content_type='text/plain',
							body=_apple_touch)


@view_config(name='favicon.ico')
def favicon_view(context, request):
	return _fi_response


@view_config(name='apple-touch-icon.png')
def apple_touch_icon_view(context, request):
	return _apple_touch_response


@view_config(name='robots.txt')
def robotstxt_view(context, request):
	return _robots_response
