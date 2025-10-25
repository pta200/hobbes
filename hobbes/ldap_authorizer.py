import os
import logging

import ldap3
from ldap3 import Server, Connection, ALL

from flower.views import BaseHandler

logger = logging.getLogger(__name__)

auth_domain = os.getenv("AUTH_DOMAIN", "")
ldap_uri = os.getenv("LDAP_SERVER_URI", "")


class LDAPHandler(BaseHandler):
    def _authenticate(self, username: str, password: str):
        """
        do simple bind on ldap for AD expect the username in UPN format e.g. user@yourdomain.com
        """
        try:
            server = Server(ldap_uri, connect_timeout=5, get_info=ALL)
            conn = Connection(
                server,
                user=username,
                password=password,
                auto_bind=True,
                raise_exceptions=True,  # raises exception on connection failure
                receive_timeout=10,
                client_strategy=ldap3.SAFE_SYNC,
            )
            return True

        except Exception as error:
            logger.error(error)
            return False

        finally:
            if conn:
                conn.unbind()

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get_template_path(self):
        # over default handler to load custom login template
        return os.path.join(os.path.dirname(__file__), "flower_templates")

    def get(self):
        if self.get_secure_cookie("user"):
            next_ = self.get_argument(
                "next", self.application.options.url_prefix or "/"
            )
            if self.application.options.url_prefix and next_[0] != "/":
                next_ = "/" + next_
            self.redirect(next_)

        else:
            self.render("login.html", message="")

    def post(self):
        """
        Handle Tornado post request from login page. Check for crendentials, authenticate
        redirect accordingly
        """
        if not self.get_argument("username") or not self.get_argument("password"):
            self.render("login.html", message="missing credentials")

        else:
            username = f"{self.get_argument('username')}@{auth_domain}"
            if self._authenticate(username, self.get_argument("password")):
                self.set_secure_cookie("user", username)
                next_ = self.get_argument(
                    "next", self.application.options.url_prefix or "/"
                )
                if self.application.options.url_prefix and next_[0] != "/":
                    next_ = "/" + next_
                self.redirect(next_)
            else:
                self.render("login.html", message="invalid credentials")
