# -*- coding: utf-8 -*-
import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from ordermanager.lib.base import BaseController, render

import ordermanager.model as model
import ordermanager.model.meta as meta

import ordermanager.lib.helpers as h

from sqlalchemy.orm import eagerload

log = logging.getLogger(__name__)

class MainController(BaseController):

    def index(self):
        qorder = meta.Session.query(model.Order).filter_by(deleted=False)
        # Filter old orders (more than 1 year old)
        max_age = request.params.get('max_age_in_days', '365')
        if len(max_age) and max_age != 'unlimited':
            qorder = qorder.filter("age(orders.created) < interval ':age days'").params(age=int(max_age))
        freeorders = qorder.filter_by(status_id=1)  # .limit(10) #
        if (session.get('preferences') or dict()).get('upcat') is not None:
            c.upcat = meta.Session.query(model.UpperCategory).filter_by(url_text=session['preferences']['upcat']).one()
            freeorders = freeorders.filter_by(upcat_id=c.upcat.id)
        c.numfree = freeorders.count()
        c.freeorders = freeorders.order_by(model.sql.desc(model.Order.created))[:10]
        if session.has_key('division') and h.have_role('performer'): #session.has_key('performer') and session['performer']:
            # Заявки, выполняемые моим подразделением
            c.mydivorders = qorder.filter("status_id<>:value and perf_id=:perf").params(value=4, perf=session['division']).order_by(model.sql.desc(model.Order.created))[:10]
            # Заявки, выполняемые мной
            myperf = qorder.filter(model.sql.not_(model.Order.status_id.in_([1, 3, 4, 5])))
            myperf = myperf.filter(model.Order.performers.any(id=session['id']))
            c.myperforming = myperf.order_by(model.Order.created)[:10]
            # Жалобы!
            c.complaints = qorder.filter("status_id=:value and perf_id=:perf").params(value=6, perf=session['division']).order_by(model.Order.created).all()
        if session.has_key('division') and session.has_key('creator') and session['creator']:
            c.myownorders = qorder.filter("cust_id=:div").params(div=session['division']).order_by(model.sql.desc(model.Order.created))[:10]
            orderstoapprove = qorder.filter("status_id=:value and cust_id=:perf").params(value=3, perf=session['division'])
            c.orderstoapprove = orderstoapprove.order_by(model.Order.created)[:10]
            c.numtoapprove = orderstoapprove.count()
        # Немножко статистики на главную
        c.ordercount = meta.Session.query(model.Order).filter_by(deleted=False).count()
        statuses = meta.Session.query(model.Status).filter(model.Status.redirects==model.Status.id)\
            .order_by(model.Status.id).all()
        c.ordercountbystatus = [(unicode(status.title), status.ordercount) for status in statuses]

        return render('/main.html')
