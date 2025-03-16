from odoo import http, fields
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request
from odoo.addons.portal.controllers.web import Home

import logging

_logger = logging.getLogger(__name__)


class AuthSignupHomeExtended(AuthSignupHome):
    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        response = super(AuthSignupHomeExtended, self).web_auth_signup(*args, **kw)

        if 'error' not in response.qcontext:
            user = request.env['res.users'].sudo().search([('login', '=', kw.get('login'))], limit=1)

            if user:
                assignment_user_id = request.env['ir.config_parameter'].sudo().get_param(
                    'education_base.assignment_user_id')

                update_values = {
                    'partner_type': kw.get('partner_type'),
                    'last_name': kw.get('last_name'),
                    'country_id': int(kw.get('country_id')) if kw.get('country_id') else False,
                    'birth_date': kw.get('birth_date'),
                    'user_gender': kw.get('user_gender'),
                }

                if kw.get('partner_type') == 'parent':
                    update_values.update({
                        'is_company': True,
                        'parent_selected_school': kw.get('other_school')
                    })

                elif kw.get('partner_type') == 'student':
                    update_values.update({
                        'student_parent_id': int(kw.get('student_parent_id')) if kw.get('student_parent_id') else None,
                    })

                    school_id = int(kw.get('hidden_school_id'))

                    if school_id == 0 and kw.get('other_school'):
                        new_school = request.env['res.partner'].sudo().create({
                            'name': kw.get('other_school'),
                            'is_company': True,
                            'company_type': 'company',
                            'partner_type': 'school',
                            'country_id': int(kw.get('country_id')) if kw.get('country_id') else False,
                            'is_assign': True,
                        })
                        school_id = new_school.id

                        if assignment_user_id:
                            assignment_user = request.env['res.users'].sudo().browse(int(assignment_user_id))
                            request.env['mail.activity'].sudo().create({
                                'res_model_id': request.env.ref('base.model_res_partner').id,
                                'res_id': school_id,
                                'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
                                'summary': 'School registration will be checked',
                                'user_id': assignment_user.id,
                                'note': 'This is an automatically generated activity. If school is correct, then remove the tick of Contacts to assign field',
                                'date_deadline': fields.Date.today(),
                            })

                    teacher_id = int(kw.get('teacher_id')[0]) if isinstance(kw.get('teacher_id'), tuple) else int(
                        kw.get('teacher_id')) if kw.get('teacher_id') else None
                    if teacher_id == 0:
                        teacher_id = None

                    update_values.update({
                        'teacher_id': teacher_id,
                        'school_id': school_id,
                    })

                    school_partner = request.env['res.partner'].sudo().browse(school_id)
                    if school_partner and school_partner.user_id:
                        update_values['user_id'] = school_partner.user_id.id

                elif kw.get('partner_type') == 'teacher':
                    school_id = int(kw.get('hidden_school_id')) if kw.get('hidden_school_id') else False

                    if school_id == 0 and kw.get('other_school'):
                        new_school = request.env['res.partner'].sudo().create({
                            'name': kw.get('other_school'),
                            'is_company': True,
                            'company_type': 'company',
                            'partner_type': 'school',
                            'country_id': int(kw.get('country_id')) if kw.get('country_id') else False,
                            'is_assign': True,
                        })
                        school_id = new_school.id

                        if assignment_user_id:
                            assignment_user = request.env['res.users'].sudo().browse(int(assignment_user_id))
                            request.env['mail.activity'].sudo().create({
                                'res_model_id': request.env.ref('base.model_res_partner').id,
                                'res_id': school_id,
                                'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
                                'summary': 'School registration will be checked',
                                'user_id': assignment_user.id,
                                'note': 'This is an automatically generated activity. If school is correct, then remove the tick of Contacts to assign field',
                                'date_deadline': fields.Date.today(),
                            })

                    if school_id:
                        update_values.update({
                            'school_id': school_id,
                            'phone': kw.get('phone'),
                        })

                        school_partner = request.env['res.partner'].sudo().browse(school_id)
                        if school_partner and school_partner.user_id:
                            update_values['user_id'] = school_partner.user_id.id

                elif kw.get('partner_type') == 'parent':
                    school_id = int(kw.get('hidden_school_id'))
                    if school_id != 0:
                        update_values['school_id'] = school_id

                user.partner_id.sudo().write(update_values)

        return response


class SchoolController(http.Controller):
    @http.route('/get_schools', type='json', auth='public', csrf=False)
    def get_schools(self, **kw):
        country_id = kw.get('country_id')
        school_search = kw.get('school_search', '')

        if not country_id:
            _logger.info("No country_id provided.")
            return {'result': []}

        try:
            country_id = int(country_id)
        except ValueError:
            return {'result': []}

        domain = [
            ('partner_type', '=', 'school'),
            ('country_id', '=', country_id)
        ]

        if school_search:
            domain.append(('name', 'ilike', school_search))

        schools = request.env['res.partner'].sudo().search(domain)
        school_list = [{'id': school.id, 'name': school.name} for school in schools]

        _logger.info(f"Found schools: {school_list}")

        return {'result': school_list}



class TeacherController(http.Controller):
    @http.route('/get_teachers', type='json', auth='public', csrf=False)
    def get_teachers(self, **kw):
        school_id = kw.get('hidden_school_id')

        if not school_id:
            _logger.info("No school_id provided.")
            return {'result': []}

        try:
            school_id = int(school_id)
        except ValueError:
            _logger.error(f"Invalid school_id: {school_id}")
            return {'result': []}

        _logger.info(f"Searching for teachers with school_id: {school_id}")

        teachers = request.env['res.partner'].sudo().search([
            ('partner_type', '=', 'teacher'),
            ('school_id', '=', school_id)
        ])
        teacher_list = [{'id': teacher.id, 'name': teacher.name} for teacher in teachers]

        _logger.info(f"Found teachers: {teacher_list}")
        return {'result': teacher_list}


class CustomWebsite(Home):

    def _login_redirect(self, uid, redirect=None):
        """ Redirect regular users (employees) to the backend and others to the frontend """
        if not redirect and request.params.get('login_success'):
            if request.env['res.users'].browse(uid)._is_internal():
                redirect = '/web?' + request.httprequest.query_string.decode()
            else:
                redirect = '/'  # Burada '/my' yerine '/' yönlendiriyoruz
        return super(CustomWebsite, self)._login_redirect(uid, redirect=redirect)


