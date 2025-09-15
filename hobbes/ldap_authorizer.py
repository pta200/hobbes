import json
import os
import re
import uuid
import logging
from urllib.parse import urlencode

import tornado.auth
import os
import tornado.gen
import tornado.web

import tornado
from tornado.options import options

from flower.views import BaseHandler

logger = logging.getLogger(__name__)



class LDAPHandler(BaseHandler):

    def get_current_user(self):
        return self.get_secure_cookie('user')

    def get_template_path(self):
        # over default handler to load custom login template
        return os.path.join(os.path.dirname(__file__), "flower_templates")


    def get(self):
        if self.get_secure_cookie('user'):
            next_ = self.get_argument('next', self.application.options.url_prefix or '/')
            if self.application.options.url_prefix and next_[0] != '/':
                next_ = '/' + next_
            self.redirect(next_)

        else:
            # self.write('<html><body><form action="/login" method="post">'
            #            'Name: <input type="text" name="name">'
            #            '<input type="submit" value="Sign in">'
            #            '</form></body></html>')

            message=''

            self.render('login.html', message=message)

    def post(self):
        logger.info("SET USER......")
        cookie = f"{self.get_argument('name')}@gmail.com"
        logger.info(cookie)
        self.set_secure_cookie("user", cookie)
        next_ = self.get_argument('next', self.application.options.url_prefix or '/')
        if self.application.options.url_prefix and next_[0] != '/':
            next_ = '/' + next_
        self.redirect(next_)
