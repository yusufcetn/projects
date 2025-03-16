import base64
import logging
from wsgiref.util import request_uri

from werkzeug.utils import redirect

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.fields import Date
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import ValidationError
from odoo.http import request, route
from odoo.osv.expression import AND, OR


_logger = logging.getLogger(__name__)

class PortalWizardImportContacts(http.Controller):

    @http.route('/my/<string:page_name>s/import', type='http', auth='user', methods=['POST', 'GET'], website=True)
    def portal_import_contacts(self, page_name, **post):

        if 'file' in post:
            file_content = post.get('file')  # Dosya içeriğini al

            current_user = request.env.user

            # page_name'e göre partner_type değerini belirleme
            partner_type_mapping = {
                'student': 'student',
                'teacher': 'teacher',
                'school': 'school',
                'subpartner': 'subpartner',
                'parent': 'parent'
            }

            partner_type = partner_type_mapping.get(page_name, 'contact')

            if not file_content:
                return request.redirect('/my/{}s/import'.format(page_name))  # Dosya yoksa tekrar formu göster

            file_data = file_content.read()
            file_base64 = base64.b64encode(file_data).decode('utf-8')

            wizard = request.env['wizard.import.contact'].sudo().create({
                'name': file_base64,  # Dosya içeriği
            })

            wizard.import_contact(partner_type, current_user)  # partner_type parametresini ekliyoruz

            return request.redirect('/my/{}s'.format(page_name))  # Dinamik sayfaya yönlendir

        return request.render('portal_contacts.portal_import_contact_form', {
            'page_name': page_name
        })

    @http.route('/enroll_to_course', type='json', auth='user')
    def enroll_to_course(self, contact_ids, course_id):
        if not contact_ids or not course_id:
            return {'success': False, 'error': 'Invalid data'}

        current_user = request.env.user
        partner_id = current_user.partner_id

        if partner_id.coin_credit_point < len(contact_ids):
            return {'success': False, 'error': 'Not enough credit points'}

        contacts = request.env['res.partner'].sudo().search([('id', 'in', contact_ids)])
        course_id = request.env['slide.channel'].sudo().search([('id', '=', int(course_id))], limit=1)
        count = 0
        message = ""

        SlideChannelPartner = request.env['slide.channel.partner'].sudo()

        for contact in contacts:
            existing_enrollment = SlideChannelPartner.sudo().search([
                ('channel_id', '=', int(course_id.id)),
                ('partner_id', '=', int(contact.id)),
                ('active', 'in', [True, False])
            ], limit=1)

            if existing_enrollment:
                message += f"ID: {contact.student_number}, Name: {contact.name} is already enrolled in this course.\n"
                continue
            else:
                SlideChannelPartner.create({
                    'channel_id': int(course_id.id),
                    'partner_id': int(contact.id),
                    'active': True,
                })
                count += 1

        if partner_id.coin_credit_point >= count != 0:
            partner_id.coin_credit_point -= count


        return {'success': True,
                'message': message.strip()
                }


class ContactsCustomerPortal(CustomerPortal):

    def _get_optional_fields(self):
        optional_fields = super(ContactsCustomerPortal, self)._get_optional_fields()
        optional_fields.append('birth_date')
        optional_fields.append('user_gender')
        return optional_fields

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        Partner = request.env["res.partner"]
        if "contact_count" in counters:
            values["contact_count"] = Partner.search_count(self._contacts_domain())
        return values

    def _contacts_domain(self, partner_type=None):
        """Get user's contacts domain."""
        domain = [("type", "=", "contact"), ("active", "=", True)]
        if partner_type:
            domain.append(("partner_type", "=", partner_type))
        domain += request.env.ref(
            "portal_contacts.rule_edit_own_contacts"
        )._compute_domain("res.partner", "read")
        domain += [("id", "!=", request.env.user.partner_id.id)]
        return domain

    def _get_archive_groups(
        self,
        model,
        domain=None,
        fields=None,
        groupby="create_date",
        order="create_date desc",
    ):
        if not model:
            return []
        if domain is None:
            domain = []
        if fields is None:
            fields = ["name", "create_date"]
        groups = []
        for group in request.env[model].read_group(
            domain, fields=fields, groupby=groupby, orderby=order
        ):
            label = group[groupby]
            date_begin = date_end = None
            for leaf in group["__domain"]:
                if leaf[0] == groupby:
                    if leaf[1] == ">=":
                        date_begin = leaf[2]
                    elif leaf[1] == "<":
                        date_end = leaf[2]
            groups.append(
                {
                    "date_begin": Date.to_string(Date.from_string(date_begin)),
                    "date_end": Date.to_string(Date.from_string(date_end)),
                    "name": label,
                    "item_count": group[groupby + "_count"],
                }
            )
        return groups

    def _get_contact_search_domain(self, search_in, search):
        search_domain = []
        if search_in == "all":
            search_domain = OR(
                [
                    search_domain,
                    [
                        "|",
                        "|",
                        "|",
                        "|",
                        ("name", "ilike", search),
                        ("last_name", "ilike", search),
                        ("phone", "ilike", search),
                        ("email", "ilike", search),
                        ("age_category", "in",
                         request.env['age.category'].sudo().search([('name', 'ilike', search)]).ids),
                    ],
                ]
            )
        elif search_in == "country":
            search_domain = [("country_id.name", "ilike", search)]
        elif search_in == "school":
            search_domain = [("school_id.name", "ilike", search)]
        elif search_in == "teacher":
            search_domain = [("teacher_id.name", "ilike", search)]
        elif search_in == "age_category":
            category_ids = request.env['age.category'].sudo().search([('name', 'ilike', search)]).ids
            search_domain = [("age_category", "in", category_ids)]
        elif search_in == "enrolled_courses":
            SlideChannelPartner = request.env['slide.channel.partner'].sudo()
            channel_partners = SlideChannelPartner.search([
                ('channel_id.name', 'ilike', search),
                ('active', '=', True)
            ])
            partner_ids = channel_partners.mapped('partner_id').ids
            search_domain = [('id', 'in', partner_ids)]

        return search_domain

    def _prepare_contacts_values(
            self, page=1, date_begin=None, date_end=None, search="", search_in="all", partner_type=None
    ):
        """Prepare the rendering context for the contacts list."""
        values = self._prepare_portal_layout_values()
        Partner = request.env["res.partner"]
        base_url = f"/my/{partner_type}s"

        # Get the required domains
        domain = self._contacts_domain(partner_type)

        logged_in_partner = request.env.user.partner_id
        if logged_in_partner.partner_type == "partner":
            domain.append(('educator_partner_id', '=', logged_in_partner.id))
        elif logged_in_partner.partner_type == "subpartner":
            domain.append(('educator_subpartner_id', '=', logged_in_partner.id))
        elif logged_in_partner.partner_type == "school":
            domain.append(('school_id', '=', logged_in_partner.id))
        elif logged_in_partner.partner_type == "teacher":
            domain.append(('teacher_id', '=', logged_in_partner.id))
        elif logged_in_partner.partner_type == "parent":
            domain.append(('student_parent_id', '=', logged_in_partner.id))

        archive_groups = self._get_archive_groups("res.partner", domain)

        searchbar_inputs = {
            "all": {"input": "all", "label": _("Search in All")},
            "country": {"input": "country", "label": _("Search by Country")},
            "school": {"input": "school", "label": _("Search by School")},
            "teacher": {"input": "teacher", "label": _("Search by Teacher")},
            "age_category": {"input": "age_category", "label": _("Search by Age Category")},
            "enrolled_courses": {"input": "enrolled_courses", "label": _("Search by Enrolled Courses")},
        }

        if search and search_in:
            domain += self._get_contact_search_domain(search_in, search)

        if date_begin and date_end:
            domain += [
                ("create_date", ">=", date_begin),
                ("create_date", "<", date_end),
            ]

        # Make pager
        pager = request.website.pager(
            url=base_url,
            url_args={"date_begin": date_begin, "date_end": date_end},
            total=Partner.search_count(domain),
            page=page,
            step=self._items_per_page,
        )

        total_contacts_count = Partner.search_count(domain)
        contacts = Partner.search(
            domain, limit=self._items_per_page, offset=pager["offset"], order="create_date desc"
        )
        request.session["my_contacts_history"] = contacts.ids[:100]

        enrolled_courses = {}
        attendee_events = {}

        if partner_type == 'student':
            SlideChannelPartner = request.env['slide.channel.partner'].sudo()
            EventRegistration = request.env['event.registration'].sudo()

            for contact in contacts:
                channel_partners = SlideChannelPartner.search([
                    ('partner_id', '=', contact.id),
                    ('active', '=', True)
                ])
                enrolled_courses[contact.id] = channel_partners.mapped('channel_id')

                event_registrations = EventRegistration.search([
                    ('partner_id', '=', contact.id),
                    ('state', 'not in', ['draft', 'cancel'])
                ])
                attendee_events[contact.id] = event_registrations.mapped('event_id')

        values.update(
            {
                "date": date_begin,
                "contacts": contacts,
                "total_contacts": total_contacts_count,
                "page_name": 'contact',
                "pager": pager,
                "archive_groups": archive_groups,
                "default_url": base_url,
                "search": search,
                "search_in": search_in,
                "searchbar_inputs": searchbar_inputs,
                'enrolled_courses': enrolled_courses,
                'attendee_events': attendee_events,
            }
        )
        return values

    def _contacts_fields(self, partner_type=None):
        fields = ['email', 'name']  # Varsayılan alanlar
        if partner_type == 'student':
            fields.extend([
                'last_name', 'phone', 'student_number', 'school_id',
                'country_id', 'user_gender', 'birth_date', 'age_category',
                'teacher_id', 'student_parent_id',
            ])
        elif partner_type == 'teacher':
            fields.extend([
                'last_name', 'phone', 'student_number', 'school_id',
                'country_id', 'user_gender', 'birth_date',
            ])
        elif partner_type == 'parent':
            fields.extend([
                'last_name', 'phone', 'student_number', 'student_id',
                'country_id', 'user_gender', 'birth_date',
            ])
        elif partner_type == 'school':
            fields.extend([
                'student_number', 'phone', 'country_id'
            ])
        elif partner_type == 'subpartner':
            fields.extend([
                'student_number', 'phone', 'country_id', 'user_gender', 'birth_date',
            ])

        return fields

    def _contacts_fields_check(self, received, partner_type=None):
        """Check received fields match those available."""

        allowed_fields = set(self._contacts_fields(partner_type if partner_type else None))
        allowed_fields.add('partner_type')  # 'partner_type' alanını izin verilen alanlara ekliyoruz
        disallowed = set(received) - allowed_fields
        if disallowed:
            raise ValidationError(_("Fields not available: %s") % ", ".join(disallowed))

    def _contacts_clean_values(self, values):
        """Set values to a write-compatible format"""
        result = {k: v or False for k, v in values.items()}
        result.setdefault("type", "contact")

        partner_type = values.get('partner_type')

        if partner_type:
            result['partner_type'] = partner_type

        if partner_type in ['subpartner', 'school']:
            result['is_company'] = True

        if request.env.user.partner_id.partner_type == 'partner':
            result.setdefault("educator_partner_id", request.env.user.partner_id.id)
        elif request.env.user.partner_id.partner_type == 'subpartner':
            result.setdefault("educator_subpartner_id", request.env.user.partner_id.id)
        elif request.env.user.partner_id.partner_type == 'school':
            result.setdefault("school_id", request.env.user.partner_id.id)
        elif request.env.user.partner_id.partner_type == 'teacher':
            result.setdefault("teacher_id", request.env.user.partner_id.id)
            if partner_type == 'student':
                result.setdefault('school_id', request.env.user.partner_id.school_id.id)
        elif request.env.user.partner_id.partner_type == 'parent':
            result.setdefault("student_parent_id", request.env.user.partner_id.id)

        return result

    @http.route(
        ["/my/contacts", "/my/contacts/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_contacts(
        self, page=1, date_begin=None, date_end=None, search="", search_in="", **kw
    ):
        return redirect("/my")

    @http.route(
        ["/my/subpartners", "/my/subpartners/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_subpartners(
            self, page=1, date_begin=None, date_end=None, search="", search_in="", **kw
    ):
        values = self._prepare_contacts_values(page, date_begin, date_end, search, search_in, partner_type="subpartner")
        values.update({"page_name": "subpartner"})
        return request.render("portal_contacts.portal_my_contacts", values)

    @http.route(
        ["/my/schools", "/my/schools/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_schools(
            self, page=1, date_begin=None, date_end=None, search="", search_in="", **kw
    ):
        values = self._prepare_contacts_values(page, date_begin, date_end, search, search_in, partner_type="school")
        values.update({"page_name": "school"})
        return request.render("portal_contacts.portal_my_contacts", values)

    @http.route(
        ["/my/teachers", "/my/teachers/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_teachers(
            self, page=1, date_begin=None, date_end=None, search="", search_in="", **kw
    ):
        values = self._prepare_contacts_values(page, date_begin, date_end, search, search_in,partner_type="teacher")
        values.update({"page_name": "teacher"})
        return request.render("portal_contacts.portal_my_contacts", values)

    @http.route(
        ["/my/students", "/my/students/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_students(
            self, page=1, date_begin=None, date_end=None, search="", search_in="", **kw
    ):
        courses = request.env['slide.channel'].sudo().search([])
        values = self._prepare_contacts_values(page, date_begin, date_end, search, search_in, partner_type="student")
        values.update({"page_name": "student"})
        values.update({"courses": courses})
        return request.render("portal_contacts.portal_my_contacts", values)

    @http.route(
        ["/my/parents", "/my/parents/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_parents(
            self, page=1, date_begin=None, date_end=None, search="", search_in="", **kw
    ):
        values = self._prepare_contacts_values(page, date_begin, date_end, search, search_in, partner_type="parent")
        values.update({"page_name": "parent"})
        return request.render("portal_contacts.portal_my_contacts", values)

    @http.route("/my/subpartners/new", auth="user", website=True)
    def portal_my_subpartners_new(self):
        """Form to create a contact for subpartners."""
        contact = request.env["res.partner"].new()
        values = self._prepare_portal_layout_values()

        values.update(
            {
                "contact": contact,
                "page_name": "add_contact",
                "fields": self._contacts_fields('subpartner'),
                "partner_type": "subpartner",
            }
        )
        return request.render("portal_contacts.portal_my_contact", values)

    @http.route("/my/schools/new", auth="user", website=True)
    def portal_my_schools_new(self):
        """Form to create a contact for schools."""
        contact = request.env["res.partner"].new()
        values = self._prepare_portal_layout_values()

        values.update(
            {
                "contact": contact,
                "page_name": "add_contact",
                "fields": self._contacts_fields('school'),
                "partner_type": "school",
            }
        )
        return request.render("portal_contacts.portal_my_contact", values)

    @http.route("/my/teachers/new", auth="user", website=True)
    def portal_my_teachers_new(self):
        """Form to create a contact for teachers."""
        contact = request.env["res.partner"].new()
        values = self._prepare_portal_layout_values()

        values.update(
            {
                "contact": contact,
                "page_name": "add_contact",
                "fields": self._contacts_fields('teacher'),
                "partner_type": "teacher",
            }
        )
        return request.render("portal_contacts.portal_my_contact", values)

    @http.route("/my/parents/new", auth="user", website=True)
    def portal_my_parents_new(self):
        """Form to create a contact for teachers."""
        contact = request.env["res.partner"].new()
        values = self._prepare_portal_layout_values()

        values.update(
            {
                "contact": contact,
                "page_name": "add_contact",
                "fields": self._contacts_fields('parent'),
                "partner_type": "parent",
            }
        )
        return request.render("portal_contacts.portal_my_contact", values)

    @http.route("/my/students/new", auth="user", website=True)
    def portal_my_students_new(self):
        """Form to create a contact for students."""
        contact = request.env["res.partner"].new()
        values = self._prepare_portal_layout_values()

        values.update(
            {
                "contact": contact,
                "page_name": "add_contact",
                "fields": self._contacts_fields('student'),
                "partner_type": "student",
            }
        )
        return request.render("portal_contacts.portal_my_contact", values)

    @http.route("/my/contacts/create", auth="user", website=True)
    def portal_my_contacts_create(self, redirect="/my/contacts/{}", **kwargs):
        """Create a contact."""
        Partner = request.env["res.partner"]
        partner_type = kwargs.get('partner_type')
        self._contacts_fields_check(kwargs.keys(), partner_type)
        values = self._contacts_clean_values(kwargs)
        _logger.debug("Creating contact with: %s", values)

        existing_user = request.env['res.users'].sudo().search([('login', '=', values.get('email'))], limit=1)

        if existing_user:
            raise UserError(_("A user with email '%s' already exists. Contact creation aborted.") % values.get('email'))

        contact = Partner.sudo().create(values)

        user_vals = {
            'partner_id': contact.id,
            'login': contact.email,
            'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
        }
        user = request.env['res.users'].sudo().create(user_vals)
        user.action_reset_password()

        return request.redirect_query(redirect.format(contact.id))

    @http.route("/my/contacts/<int:contact>", type="http", auth="public", website=True)
    def portal_my_contacts_read(self, contact=None, access_token=None, **kw):
        """Read a contact form."""
        try:
            contact_sudo = self._document_check_access(
                "res.partner", contact, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        values = self._contact_get_page_view_values(contact_sudo, access_token, **kw)
        return request.render("portal_contacts.portal_my_contact", values)

    # ------------------------------------------------------------
    # My Contact
    # ------------------------------------------------------------
    def _contact_get_page_view_values(self, contact, access_token, **kwargs):
        fields = self._contacts_fields(contact.partner_type)

        related_fields = {
            "teacher_name": contact.teacher_id.full_name if contact.teacher_id else "",
            "teacher_email": contact.teacher_id.email if contact.teacher_id else "",
            "teacher_phone": contact.teacher_id.phone if contact.teacher_id else "",
            "parent_name": contact.student_parent_id.full_name if contact.student_parent_id else "",
            "parent_email": contact.student_parent_id.email if contact.student_parent_id else "",
            "parent_phone": contact.student_parent_id.phone if contact.student_parent_id else "",
            "school_name": contact.school_id.name if contact.school_id else "",
            "country_name": contact.country_id.name if contact.country_id else "",
            "student_teacher_name": contact.student_id.teacher_id.full_name if contact.student_id and contact.student_id.teacher_id else "",
            "student_teacher_email": contact.student_id.teacher_id.email if contact.student_id and contact.student_id.teacher_id else "",
            "student_teacher_phone": contact.student_id.teacher_id.phone if contact.student_id and contact.student_id.teacher_id else "",
            "student_school_name": contact.student_id.school_id.name if contact.student_id and contact.student_id.school_id else "",  # Yeni eklenen satır
            "age_category": contact.age_category.name if contact.age_category else "",
        }

        values = {
            "page_name": "contact",
            "contact": contact,
            "fields": fields,
            **related_fields,
        }
        return self._get_page_view_values(
            contact, access_token, values, "my_contacts_history", False, **kwargs
        )

    @http.route("/my/contacts/<int:contact>/update", auth="user", website=True)
    def portal_my_contacts_update(self, contact, redirect="/my/contacts/{}", **kwargs):
        """Update a contact."""
        contact = request.env["res.partner"].sudo().browse(int(contact))
        self._contacts_fields_check(kwargs.keys(), contact.partner_type)
        values = self._contacts_clean_values(kwargs)
        if kwargs.get('country_id'):
            country = request.env["res.country"].sudo().browse(int(kwargs.get('country_id')))
            values.update({'country_id': country})
        values.update({'partner_type': contact.partner_type})
        _logger.debug("Updating %r with: %s", contact, values)
        contact.write(values)
        return request.redirect_query(redirect.format(contact.id))

    @http.route("/my/contacts/<int:contact>/disable", auth="user", website=True)
    def portal_my_contacts_disable(self, contact, redirect="/my/contacts"):
        """Disable a contact."""
        contact = request.env["res.partner"].browse(int(contact))
        _logger.debug("Disabling %r", contact)
        contact.sudo().active = False
        return request.redirect_query(redirect)

    # ContactsCustomerPortal sınıfına eklenecek yeni metodlar:

    def _get_export_fields(self, partner_type=None):
        """Get fields to be exported based on partner type"""
        export_fields = {
            'student': {
                'ID': 'student_number',
                'Name': 'name',
                'Last Name': 'last_name',
                'Email': 'email',
                'Phone': 'phone',
                'Birth Date': 'birth_date',
                'Gender': 'user_gender',
                'Age Category': 'age_category.name',
                'School': 'school_id.name',
                'Country': 'country_id.name',
                'Teacher': 'teacher_id.name',
                'Parent': 'student_parent_id.name',
                'Enrolled Courses': 'enrolled_courses'
            },
            'teacher': {
                'ID': 'student_number',
                'Name': 'name',
                'Last Name': 'last_name',
                'Email': 'email',
                'Phone': 'phone',
                'Birth Date': 'birth_date',
                'Gender': 'user_gender',
                'School': 'school_id.name',
                'Country': 'country_id.name'
            },
            'school': {
                'ID': 'student_number',
                'Name': 'name',
                'Email': 'email',
                'Phone': 'phone',
                'Country': 'country_id.name'
            },
            'subpartner': {
                'ID': 'student_number',
                'Name': 'name',
                'Email': 'email',
                'Phone': 'phone',
                'Birth Date': 'birth_date',
                'Gender': 'user_gender',
                'Country': 'country_id.name'
            },
            'parent': {
                'ID': 'student_number',
                'Name': 'name',
                'Last Name': 'last_name',
                'Email': 'email',
                'Phone': 'phone',
                'Birth Date': 'birth_date',
                'Gender': 'user_gender',
                'Student': 'student_id.name',
                'Country': 'country_id.name'
            }
        }
        return export_fields.get(partner_type, {})

    @http.route(['/my/<string:page_name>s/export'], type='http', auth='user', website=True, csrf=False)
    def export_contacts(self, page_name, **kw):
        try:
            import xlsxwriter
            import io
            from datetime import datetime

            partner_type_mapping = {
                'student': 'student',
                'teacher': 'teacher',
                'school': 'school',
                'subpartner': 'subpartner',
                'parent': 'parent'
            }
            partner_type = partner_type_mapping.get(page_name)

            if not partner_type:
                return request.redirect('/my')

            if not request.env.user or not request.env.user.partner_id:
                return request.redirect('/web/login')

            domain = self._contacts_domain(partner_type)

            logged_in_partner = request.env.user.partner_id
            if logged_in_partner.partner_type == "partner":
                domain.append(('educator_partner_id', '=', logged_in_partner.id))
            elif logged_in_partner.partner_type == "subpartner":
                domain.append(('educator_subpartner_id', '=', logged_in_partner.id))
            elif logged_in_partner.partner_type == "school":
                domain.append(('school_id', '=', logged_in_partner.id))
            elif logged_in_partner.partner_type == "teacher":
                domain.append(('teacher_id', '=', logged_in_partner.id))
            elif logged_in_partner.partner_type == "parent":
                domain.append(('student_parent_id', '=', logged_in_partner.id))

            Partner = request.env['res.partner']

            with request.env.cr.savepoint():
                contacts = Partner.search(domain)

                enrolled_courses = {}
                if partner_type == 'student':
                    SlideChannelPartner = request.env['slide.channel.partner'].sudo()
                    for contact in contacts:
                        channel_partners = SlideChannelPartner.search([
                            ('partner_id', '=', contact.id),
                            ('active', '=', True)
                        ])
                        enrolled_courses[contact.id] = ', '.join(channel_partners.mapped('channel_id.name'))

                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output)

                try:
                    worksheet = workbook.add_worksheet('Contacts')

                    header_style = workbook.add_format({
                        'bold': True,
                        'align': 'center',
                        'valign': 'vcenter',
                        'fg_color': '#D3D3D3',
                        'border': 1
                    })

                    cell_style = workbook.add_format({
                        'align': 'left',
                        'valign': 'vcenter',
                        'border': 1,
                        'text_wrap': True
                    })

                    export_fields = self._get_export_fields(partner_type)
                    headers = list(export_fields.keys())
                    field_names = list(export_fields.values())

                    for col, header in enumerate(headers):
                        worksheet.write(0, col, header, header_style)
                        if header == 'Enrolled Courses':
                            worksheet.set_column(col, col, 30)
                        else:
                            worksheet.set_column(col, col, 15)

                    for row, contact in enumerate(contacts, start=1):
                        for col, field in enumerate(field_names):
                            if field == 'enrolled_courses':
                                value = enrolled_courses.get(contact.id, 'No courses')
                            else:
                                value = contact.sudo() if field == 'age_category.name' else contact
                                for field_part in field.split('.'):
                                    value = getattr(value, field_part, '')
                            worksheet.write(row, col, value or '', cell_style)

                    workbook.close()
                    output.seek(0)

                    filename = f'{partner_type}_contacts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

                    headers = [
                        ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        ('Content-Disposition', f'attachment; filename={filename}'),
                        ('Cache-Control', 'no-cache'),
                        ('Pragma', 'no-cache'),
                        ('Expires', '0')
                    ]

                    response = request.make_response(output.read(), headers)
                    response.set_cookie('session_id', request.session.sid)
                    return response

                finally:
                    workbook.close()
                    output.close()

        except Exception as e:
            _logger.error("Export error: %s", str(e), exc_info=True)
            return request.redirect('/my')