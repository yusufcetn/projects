from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.populate import compute


class ResPartner(models.Model):
    _inherit = 'res.partner'

    full_name = fields.Char(string="Full Name", compute="_compute_full_name")
    last_name = fields.Char(string='Last Name')
    country_id = fields.Many2one('res.country', string='Country')
    birth_date = fields.Date(string='Birth date')
    user_gender = fields.Selection([('male', 'Male'),
                                    ('female', 'Female')],
                                   string='Gender')
    student_parent_id = fields.Many2one('res.partner', string='Parent', store=True)
    school_id = fields.Many2one('res.partner', string='School', store=True)
    teacher_id = fields.Many2one('res.partner', string='Teacher', store=True)
    student_number = fields.Char(string="ID Number ", readonly=False)
    educator_partner_id = fields.Many2one('res.partner', compute='_compute_partner_id', inverse='_set_partner_id', string="Partner", store=True)
    educator_subpartner_id = fields.Many2one('res.partner', compute='_compute_subpartner_id', inverse='_set_subpartner_id' , string="Sub-Partner", store=True)
    student_id =  fields.Many2one('res.partner', string='Student', store=True)

    country_group_id = fields.Many2one('res.country.group',compute='compute_country_group' ,string="Region", readonly=True)
    short_code = fields.Char(string="Short Code")
    educator_partner_code = fields.Char(compute='_compute_educator_partner_code', string="Partner Code")

    parent_email = fields.Char(string="Parent/Guardian Email", related='student_parent_id.email')
    parent_phone = fields.Char(string="Parent/Guardian Phone", related='student_parent_id.phone')

    related_subpartner_ids = fields.One2many('res.partner', 'educator_partner_id', string=" ",
                                             compute='_compute_related_partners')
    related_school_ids = fields.One2many('res.partner', 'educator_partner_id', string=" ",
                                         compute='_compute_related_partners')
    related_teacher_ids = fields.One2many('res.partner', 'school_id', string=" ",
                                          compute='_compute_related_partners')
    related_student_ids = fields.One2many('res.partner', 'school_id', string=" ",
                                          compute='_compute_related_partners')
    special_age_category = fields.Boolean(string="Special Age Category")
    age_category = fields.Many2one('age.category', compute='_compute_age_category',string='Exam/Age Category', store=True)

    parent_selected_school = fields.Char(string='Parent Selected School')

    view_selection = fields.Selection([
        ('tree', 'List View'),
        ('kanban', 'Kanban View')
    ], string="View Type", default='tree')

    # Compute alanlara import özelliği ekleme
    def fields_get(self, allfields=None, attributes=None):
        res = super(ResPartner, self).fields_get(allfields=allfields, attributes=attributes)
        fields_to_update = [
            'student_parent_id',
            'school_id',
            'teacher_id',
            'student_number',
            'educator_partner_id',
            'educator_subpartner_id',
            'student_id',
        ]
        for field in fields_to_update:
            if field in res:
                res[field]['exportable'] = True
                res[field]['importable'] = True
        return res

    def _set_partner_id(self):
        for record in self:
            record.educator_partner_id = record.educator_partner_id

    def _set_subpartner_id(self):
        for record in self:
            record.educator_subpartner_id = record.educator_subpartner_id

    @api.depends('partner_type')
    def _compute_related_partners(self):
        for record in self:
            record.related_subpartner_ids = False
            record.related_school_ids = False
            record.related_teacher_ids = False
            record.related_student_ids = False

            if record.partner_type == 'partner':
                record.related_subpartner_ids = self.env['res.partner'].search([
                    ('educator_partner_id', '=', record.id),
                    ('partner_type', '=', 'subpartner')
                ])
                record.related_school_ids = self.env['res.partner'].search([
                    ('educator_partner_id', '=', record.id),
                    ('partner_type', '=', 'school')
                ])
                record.related_teacher_ids = self.env['res.partner'].search([
                    ('educator_partner_id', '=', record.id),
                    ('partner_type', '=', 'teacher')
                ])
                record.related_student_ids = self.env['res.partner'].search([
                    ('educator_partner_id', '=', record.id),
                    ('partner_type', '=', 'student')
                ])
            elif record.partner_type == 'subpartner':
                record.related_school_ids = self.env['res.partner'].search([
                    ('educator_subpartner_id', '=', record.id),
                    ('partner_type', '=', 'school')
                ])
                record.related_teacher_ids = self.env['res.partner'].search([
                    ('educator_subpartner_id', '=', record.id),
                    ('partner_type', '=', 'teacher')
                ])
                record.related_student_ids = self.env['res.partner'].search([
                    ('educator_subpartner_id', '=', record.id),
                    ('partner_type', '=', 'student')
                ])
            elif record.partner_type == 'school':
                record.related_teacher_ids = self.env['res.partner'].search([
                    ('school_id', '=', record.id),
                    ('partner_type', '=', 'teacher')
                ])
                record.related_student_ids = self.env['res.partner'].search([
                    ('school_id', '=', record.id),
                    ('partner_type', '=', 'student')
                ])
            elif record.partner_type == 'teacher':
                record.related_student_ids = self.env['res.partner'].search([
                    ('teacher_id', '=', record.id),
                    ('partner_type', '=', 'student')
                ])
            elif record.partner_type == 'parent':
                record.related_student_ids = self.env['res.partner'].search([
                    ('student_parent_id', '=', record.id),
                    ('partner_type', '=', 'student')
                ])

    @api.depends('name', 'last_name')
    def _compute_full_name(self):
        for record in self:
            record.full_name = f"{record.name} {record.last_name}" if record.name and record.last_name else record.name or ''

    @api.depends(lambda self: (self._rec_name,) if self._rec_name else ())
    def _compute_display_name(self):

        super(ResPartner, self)._compute_display_name()

        for record in self:
            if record.last_name:
                record.display_name = f"{record.name} {record.last_name}"

    @api.depends('country_id', 'short_code')
    def _compute_educator_partner_code(self):
        for record in self:
            if record.country_id and record.short_code:
                record.educator_partner_code = f"{record.country_id.name} | {record.short_code}"
            else:
                record.educator_partner_code = ''

    @api.depends('country_id')
    def compute_country_group(self):
        for record in self:
            if record.country_id:
                country_group = self.env['res.country.group'].search([('country_ids', 'in', record.country_id.id)],limit=1)
                record.country_group_id = country_group.id if country_group else False
            else:
                record.country_group_id = False

    @api.depends('school_id', 'student_id')
    def _compute_partner_id(self):
        for record in self:
            if record.school_id and record.school_id.educator_partner_id:
                record.educator_partner_id = record.school_id.educator_partner_id
            elif record.student_id and record.student_id.school_id and record.student_id.school_id.educator_partner_id:
                record.educator_partner_id = record.student_id.school_id.educator_partner_id
            else:
                record.educator_partner_id = False

    @api.depends('school_id', 'student_id')
    def _compute_subpartner_id(self):
        for record in self:
            if record.school_id and record.school_id.educator_subpartner_id:
                record.educator_subpartner_id = record.school_id.educator_subpartner_id
            elif record.student_id and record.student_id.school_id and record.student_id.school_id.educator_subpartner_id:
                record.educator_subpartner_id = record.student_id.school_id.educator_subpartner_id
            else:
                record.educator_subpartner_id = False

    def update_related_pricelist(self, related_records, new_pricelist, updated_records):
        if related_records:
            for related_record in related_records:
                if not related_record.special_pricelist_id and related_record.id not in updated_records:
                    related_record.with_context(updated_records=updated_records | {related_record.id}).write(
                        {'property_product_pricelist': new_pricelist})

    def get_parent_pricelist(self, record):
        parent_pricelist = False

        if record.partner_type == 'teacher':
            if record.school_id:
                parent_pricelist = record.school_id.property_product_pricelist
        elif record.partner_type == 'school':
            if record.educator_subpartner_id:
                parent_pricelist = record.educator_subpartner_id.property_product_pricelist
            elif record.educator_partner_id and not record.educator_subpartner_id:
                parent_pricelist = record.educator_partner_id.property_product_pricelist
        elif record.partner_type == 'subpartner':
            if record.educator_partner_id:
                parent_pricelist = record.educator_partner_id.property_product_pricelist

        return parent_pricelist

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if vals.get('partner_type') in ['student', 'teacher'] and vals.get('company_type') == 'company':
                raise ValidationError(
                    "Contacts with the partner type 'Student' or 'Teacher' can only be saved as 'Individual'. Please select 'Individual' for company type.")

        res = super(ResPartner, self).create(vals_list)

        if res.partner_type == 'partner':
            for partner in res:
                partner.special_pricelist_id = True

        for record in res:
            if record.partner_type:
                record.student_number = self.env['ir.sequence'].next_by_code('res.partner.student.number')

        return res

    def write(self, vals):
        updated_records = self.env.context.get('updated_records', set())

        for record in self:
            partner_type = vals.get('partner_type', record.partner_type)
            company_type = vals.get('company_type', record.company_type)

            if partner_type in ['student', 'teacher'] and company_type == 'company':
                raise ValidationError(
                    "Contacts with the partner type 'Student' or 'Teacher' can only be saved as 'Individual'. Please select 'Individual' for company type.")

        res = super(ResPartner, self).write(vals)

        if 'user_id' in vals:
            for record in self:
                if record.partner_type == 'partner' and record.id not in updated_records:
                    related_models = [
                        record.related_school_ids,
                        record.related_subpartner_ids,
                        record.related_teacher_ids,
                        record.related_student_ids
                    ]

                    for model in related_models:
                        if model and model.user_id != record.user_id:
                            model.with_context(updated_records=updated_records | {record.id}).write({
                                'user_id': record.user_id
                            })
                            updated_records.add(record.id)


        if 'special_pricelist_id' in vals and not vals.get('special_pricelist_id'):
            for record in self:
                parent_pricelist = self.get_parent_pricelist(record)

                if parent_pricelist and record.property_product_pricelist != parent_pricelist:
                    record.with_context(updated_records=updated_records | {record.id}).write({
                        'property_product_pricelist': parent_pricelist.id
                    })

                    related_ids = record.related_subpartner_ids | record.related_school_ids | \
                                  record.related_teacher_ids | record.related_student_ids
                    self.update_related_pricelist(related_ids, parent_pricelist.id, updated_records)

        # Eğer partner veya okul değiştiyse, yeni partnerin veya okulun pricelist'ini alıp kaydı ve alt partnerleri güncelle
        if 'educator_partner_id' in vals or 'educator_subpartner_id' in vals or 'school_id' in vals or 'teacher_id' in vals:
            for record in self:
            # Yeni partnerin veya okulun pricelist'ini al
                new_pricelist = None
                if 'educator_partner_id' in vals and record.educator_partner_id and record.educator_partner_id.property_product_pricelist:
                    new_pricelist = record.educator_partner_id.property_product_pricelist
                elif 'educator_subpartner_id' in vals and record.educator_subpartner_id and record.educator_subpartner_id.property_product_pricelist:
                    new_pricelist = record.educator_subpartner_id.property_product_pricelist
                elif 'school_id' in vals and record.school_id and record.school_id.property_product_pricelist:
                    new_pricelist = record.school_id.property_product_pricelist
                elif 'teacher_id' in vals and record.teacher_id and record.teacher_id.property_product_pricelist:
                    new_pricelist = record.teacher_id.property_product_pricelist

                # Eğer pricelist bulunduysa, kaydın ve ilgili alt partnerlerin pricelist'ini güncelle
                if new_pricelist and record.property_product_pricelist != new_pricelist:
                    record.with_context(updated_records=updated_records | {record.id}).write({
                        'property_product_pricelist': new_pricelist.id
                    })

                    related_ids = record.related_subpartner_ids | record.related_school_ids | \
                                  record.related_teacher_ids | record.related_student_ids
                    self.update_related_pricelist(related_ids, new_pricelist.id, updated_records)

        if 'property_product_pricelist' in vals:
            for record in self:
                if record.id in updated_records:
                    continue

                new_pricelist = vals.get('property_product_pricelist')

                related_ids = record.related_subpartner_ids | record.related_school_ids | \
                              record.related_teacher_ids | record.related_student_ids
                self.update_related_pricelist(related_ids, new_pricelist, updated_records)

        if 'school_id' in vals:
            for record in self:
                if record.partner_type == 'teacher':
                    new_school_id = vals.get('school_id')
                    if new_school_id:
                        related_students = record.related_student_ids
                        related_students.write({'school_id': new_school_id})

        if 'educator_partner_id' in vals or 'educator_subpartner_id' in vals:
            for record in self:
                if record.partner_type == 'school':
                    record.related_teacher_ids._compute_partner_id()
                    record.related_student_ids._compute_partner_id()

                    record.related_teacher_ids._compute_subpartner_id()
                    record.related_student_ids._compute_subpartner_id()

        if 'school_id' in vals:
            for record in self:
                if record.partner_type == 'student' and record.student_parent_id:
                    new_school = record.school_id
                    new_partner_id = new_school.educator_partner_id.id if new_school.educator_partner_id else False
                    new_subpartner_id = new_school.educator_subpartner_id.id if new_school.educator_subpartner_id else False

                    record.student_parent_id.write({
                        'educator_partner_id': new_partner_id,
                        'educator_subpartner_id': new_subpartner_id
                    })

        if 'student_parent_id' in vals:
            for record in self:
                if record.student_parent_id and not record.student_parent_id.student_id:
                    record.student_parent_id.student_id = record.id
                    if not record.student_parent_id.user_id and record.user_id:
                        record.student_parent_id.user_id = record.user_id

        if 'partner_type' in vals:
            for record in self:
                if not record.student_number:
                    record.student_number = self.env['ir.sequence'].next_by_code('res.partner.student.number')

            for partner in self:

                if partner.partner_type =='partner':
                    partner.special_pricelist_id = True

                user = partner.user_ids and partner.user_ids[0] or None
                if user:
                    partner_type = vals.get('partner_type')

                    group_ids = [
                        self.env.ref('signup_page.group_student_user').id,
                        self.env.ref('signup_page.group_teacher_user').id,
                        self.env.ref('signup_page.group_parent_user').id,
                        self.env.ref('signup_page.group_school_user').id,
                        self.env.ref('signup_page.group_subpartner_user').id,
                        self.env.ref('signup_page.group_partner_user').id
                    ]

                    for group in user.groups_id:
                        if group.id in group_ids:
                            user.sudo().write({'groups_id': [(3, group.id)]})

                    group_mapping = {
                        'student': 'signup_page.group_student_user',
                        'teacher': 'signup_page.group_teacher_user',
                        'parent': 'signup_page.group_parent_user',
                        'school': 'signup_page.group_school_user',
                        'subpartner': 'signup_page.group_subpartner_user',
                        'partner': 'signup_page.group_partner_user'
                    }

                    if partner_type in group_mapping:
                        related_group_id = self.env.ref(group_mapping[partner_type]).id
                        user.sudo().write({'groups_id': [(4, related_group_id)]})

        return res

    @api.depends('birth_date')
    def _compute_age_category(self):
        for record in self:
            if record.birth_date and record.partner_type == 'student' and not record.special_age_category:
                birth_date = record.birth_date

                age_category = self.env['age.category'].search([
                    ('min_date', '<=', birth_date),
                    ('max_date', '>=', birth_date)
                ], limit=1)

                if age_category:
                    record.age_category = age_category.id

    @api.model
    def cron_compute_age_category(self):
        students = self.search([('partner_type', '=', 'student')])
        students._compute_age_category()

    def set_number(self):
        for record in self:
            if not record.student_number:
                record.student_number = self.env['ir.sequence'].next_by_code('res.partner.student.number')
