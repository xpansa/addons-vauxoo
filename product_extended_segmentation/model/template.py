# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2015 Vauxoo
#    Author : Humberto Arocha <hbto@vauxoo.com>
#             Osval Reyes <osval@vauxoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields
from openerp.addons.product import _common
SEGMENTATION_COST = [
    'landed_cost',
    'subcontracting_cost',
    'material_cost',
    'production_cost',
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _calc_price(
            self, cr, uid, bom, test=False, real_time_accounting=False,
            context=None):
        context = dict(context or {})
        price = 0
        uom_obj = self.pool.get("product.uom")
        quant_obj = self.pool.get("stock.quant")
        tmpl_obj = self.pool.get('product.template')
        bom_obj = self.pool.get('mrp.bom')
        prod_obj = self.pool.get('product.product')

        model = 'product.product'

        def _bom_find(prod_id):
            if model == 'product.product':
                # if not look for template
                bom_id = bom_obj._bom_find(
                    cr, uid, product_id=prod_id, context=context)
                if bom_id:
                    return bom_id
                prod_id = prod_obj.browse(
                    cr, uid, prod_id, context=context).product_tmpl_id.id
            return bom_obj._bom_find(
                cr, uid, product_tmpl_id=prod_id, context=context)

        def quant_search(product_id):
            ARGS = [('product_id', '=', product_id)]
            return quant_obj.search(
                cr, uid, ARGS, order='in_date DESC', limit=1)

        def _factor(factor, product_efficiency, product_rounding):
            factor = factor / (product_efficiency or 1.0)
            factor = _common.ceiling(factor, product_rounding)
            if factor < product_rounding:
                factor = product_rounding
            return factor

        factor = _factor(1.0, bom.product_efficiency, bom.product_rounding)

        sgmnt_dict = {}.fromkeys(SEGMENTATION_COST, 0.0)
        for sbom in bom.bom_line_ids:
            my_qty = sbom.product_qty / sbom.product_efficiency
            if sbom.attribute_value_ids:
                continue
            # No attribute_value_ids means the bom line is not variant
            # specific

            # NOTE: find for this product last quant
            quant = quant_search(sbom.product_id.id)
            # NOTE: find for this product if any bom available
            bom_id = _bom_find(sbom.product_id.id)

            if bom_id or not quant:
                # NOTE: if any bom them use segmentation on product
                obj_brw = sbom.product_id
            else:
                obj_brw = quant_obj.browse(cr, uid, quant[0], context=context)

            for fieldname in SEGMENTATION_COST:
                # NOTE: Is this price well Normalized
                price_sgmnt = uom_obj._compute_price(
                    cr, uid, sbom.product_id.uom_id.id,
                    getattr(obj_brw, fieldname),
                    sbom.product_uom.id) * my_qty
                price += price_sgmnt
                sgmnt_dict[fieldname] += price_sgmnt

        if bom.routing_id:
            for wline in bom.routing_id.workcenter_lines:
                wc = wline.workcenter_id
                cycle = wline.cycle_nbr
                d, m = divmod(factor, wc.capacity_per_cycle)
                mult = (d + (m and 1.0 or 0.0))
                hour = float(
                    wline.hour_nbr * mult + (
                        (wc.time_start or 0.0) + (wc.time_stop or 0.0) +
                        cycle * (wc.time_cycle or 0.0)) * (
                            wc.time_efficiency or 1.0))
                routing_price = wc.costs_cycle * cycle + wc.costs_hour * hour
                routing_price = uom_obj._compute_price(
                    cr, uid, bom.product_uom.id, routing_price,
                    bom.product_id.uom_id.id)
                price += routing_price
                sgmnt_dict['production_cost'] += routing_price

        # Convert on product UoM quantities
        if price > 0:
            price = uom_obj._compute_price(
                cr, uid, bom.product_uom.id, price / bom.product_qty,
                bom.product_id.uom_id.id)

        product = tmpl_obj.browse(
            cr, uid, bom.product_tmpl_id.id, context=context)
        if not test:
            if (product.valuation != "real_time" or not real_time_accounting):
                tmpl_obj.write(
                    cr, uid, [product.id], {'standard_price': price},
                    context=context)
            else:
                # Call wizard function here
                wizard_obj = self.pool.get("stock.change.standard.price")
                ctx = context.copy()
                ctx.update(
                    {'active_id': product.id,
                     'active_model': 'product.template'})
                wiz_id = wizard_obj.create(
                    cr, uid, {'new_price': price}, context=ctx)
                wizard_obj.change_price(cr, uid, [wiz_id], context=ctx)
            tmpl_obj.write(cr, uid, [product.id], sgmnt_dict, context=context)
        return price

    def compute_price(self, cr, uid, product_ids, template_ids=False,
                      recursive=False, test=False, real_time_accounting=False,
                      context=None):
        '''
        Will return test dict when the test = False
        Multiple ids at once?
        testdict is used to inform the user about the changes to be made
        '''
        bom_obj = self.pool.get('mrp.bom')
        prod_obj = self.pool.get('product.product')
        testdict = {}
        real_time = real_time_accounting
        ids = template_ids
        model = 'product.template'
        if product_ids:
            ids = product_ids
            model = 'product.product'

        def _bom_find(prod_id):
            if model == 'product.product':
                # if not look for template
                bom_id = bom_obj._bom_find(
                    cr, uid, product_id=prod_id, context=context)
                if bom_id:
                    return bom_id
                prod_id = prod_obj.browse(
                    cr, uid, prod_id, context=context).product_tmpl_id.id
            return bom_obj._bom_find(
                cr, uid, product_tmpl_id=prod_id, context=context)

        for prod_id in ids:
            bom_id = _bom_find(prod_id)
            if not bom_id:
                continue
            # In recursive mode, it will first compute the prices of child
            # boms
            if recursive:
                # Search the products that are components of this bom of
                # prod_id
                bom = bom_obj.browse(cr, uid, bom_id, context=context)

                # Call compute_price on these subproducts
                prod_set = set([x.product_id.id for x in bom.bom_line_ids])
                res = self. compute_price(
                    cr, uid, product_ids=list(prod_set), template_ids=[],
                    recursive=recursive, test=test,
                    real_time_accounting=real_time, context=context)
                if test:
                    testdict.update(res)

            # Use calc price to calculate and put the price on the product
            # of the BoM if necessary
            price = self._calc_price(
                cr, uid, bom_obj.browse(cr, uid, bom_id, context=context),
                test=test, real_time_accounting=real_time, context=context)
            if test:
                testdict.update({prod_id: price})
        if test:
            return testdict
        return True
