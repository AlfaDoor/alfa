# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import Warning, UserError
from odoo import models, fields, exceptions, api, _
import io
import tempfile
import binascii
import logging

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug("Cannot `import csv`.")
try:
    import xlwt
except ImportError:
    _logger.debug("Cannot `import xlwt`.")
try:
    import base64
except ImportError:
    _logger.debug("Cannot `import base64`.")
try:
    import xlrd
except ImportError:
    _logger.debug("Cannot `import xlrd`.")


class gen_inv(models.TransientModel):
    _name = "gen.inv"

    file = fields.Binary("File")
    inv_name = fields.Char("Inventory Name")
    location_id = fields.Many2one("stock.location", "Location")
    import_option = fields.Selection(
        [("csv", "CSV File"), ("xls", "XLS File")], string="Select", default="csv"
    )
    import_prod_option = fields.Selection(
        [("barcode", "Barcode"), ("code", "Code"), ("name", "Name")],
        string="Import Product By",
        default="code",
    )

    @api.multi
    def import_csv(self):
        stloc_obj = self.env["stock.location"]
        inventory_obj = self.env["stock.inventory"]
        if not self.location_id:
            raise Warning(_("Please Select a Location"))
        """Load Inventory data from the CSV file."""
        if self.import_option == "csv":
            keys = ["code", "quantity", "location"]
            product_obj = self.env["product.product"]
            csv_data = base64.b64decode(self.file)
            data_file = io.StringIO(csv_data.decode("utf-8"))
            data_file.seek(0)
            file_reader = []
            csv_reader = csv.reader(data_file, delimiter=",")
            try:
                file_reader.extend(csv_reader)
            except Exception:
                raise exceptions.Warning(_("Invalid file!"))
            values = {}
            inventory_id = inventory_obj.create(
                {
                    "name": self.inv_name,
                    "filter": "partial",
                    "location_id": self.location_id.id,
                }
            )
            for i in range(len(file_reader)):
                if i != 0:
                    val = {}
                    try:
                        field = list(map(str, file_reader[i]))
                    except ValueError:
                        raise exceptions.Warning(
                            _("Please don't use Characters, use numbers only.")
                        )
                    values = dict(zip(keys, field))
                    if self.import_prod_option == "barcode":
                        prod_lst = product_obj.search(
                            [("barcode", "=", values["code"])]
                        )
                    elif self.import_prod_option == "code":
                        prod_lst = product_obj.search(
                            [("default_code", "=", values["code"])]
                        )
                    else:
                        prod_lst = product_obj.search([("name", "=", values["code"])])
                    if prod_lst:
                        val["product"] = prod_lst[0].id
                        if isinstance(values["quantity"], str):
                            try:
                                values["quantity"] = float(values["quantity"])
                            except Exception:
                                raise UserError(
                                    "The data you have entered is not correct, it contains strings in the column of quantity."
                                )
                        val["quantity"] = values["quantity"]
                        loc = stloc_obj.search(
                            [
                                (
                                    "complete_name",
                                    "=",
                                    "Physical Locations/" + values["location"],
                                )
                            ]
                        )
                        if not loc:
                            raise UserError(
                                "Location %s not found in the system."
                                % "Partner Locations/"
                                + values["location"]
                            )
                        val["location"] = loc[0].id
                    if bool(val):
                        product_uom_id = product_obj.browse(val["product"]).uom_id
                        res = inventory_id.write(
                            {
                                "line_ids": [
                                    (
                                        0,
                                        0,
                                        {
                                            "product_id": val["product"],
                                            "location_id": val["location"],
                                            "product_uom_id": product_uom_id.id,
                                            "product_qty": val["quantity"],
                                        },
                                    )
                                ]
                            }
                        )
                    else:
                        raise Warning(_('Product Not Found  "%s"') % values.get("code"))
                res = inventory_obj.with_context(ids=inventory_id).prepare_inventory()
            return res
        else:
            """Load Inventory data from the EXCEL file."""
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)
            values = {}
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            inventory_id = inventory_obj.create(
                {
                    "name": self.inv_name,
                    "filter": "partial",
                    "location_id": self.location_id.id,
                }
            )
            product_obj = self.env["product.product"]
            for row_no in range(sheet.nrows):
                val = {}
                if row_no <= 0:
                    fields = map(
                        lambda row: row.value.encode("utf-8"), sheet.row(row_no)
                    )
                else:
                    line = list(
                        map(
                            lambda row: isinstance(row.value, bytes)
                            and row.value.encode("utf-8")
                            or str(row.value),
                            sheet.row(row_no),
                        )
                    )
                    if line:
                        values.update(
                            {"code": line[0], "quantity": line[1], "location": line[2]}
                        )
                        if self.import_prod_option == "barcode":
                            prod_lst = product_obj.search(
                                [("barcode", "=", values["code"])]
                            )
                        elif self.import_prod_option == "code":
                            prod_lst = product_obj.search(
                                [("default_code", "=", values["code"])]
                            )
                        else:
                            prod_lst = product_obj.search(
                                [("name", "=", values["code"])]
                            )
                        if prod_lst:
                            val["product"] = prod_lst[0].id
                            val["quantity"] = values["quantity"]
                            loc = stloc_obj.search(
                                [
                                    (
                                        "complete_name",
                                        "=",
                                        "Physical Locations/" + values["location"],
                                    )
                                ]
                            )
                            if not loc:
                                raise UserError(
                                    "Location %s not found in the system." % loc
                                )
                            val["location"] = loc[0].id
                        if bool(val):
                            product_uom_id = product_obj.browse(val["product"]).uom_id
                            res = inventory_id.write(
                                {
                                    "line_ids": [
                                        (
                                            0,
                                            0,
                                            {
                                                "product_id": val["product"],
                                                "location_id": val["location"],
                                                "product_uom_id": product_uom_id.id,
                                                "product_qty": val["quantity"],
                                            },
                                        )
                                    ]
                                }
                            )
                        else:
                            raise Warning(
                                _('Product Not Found "%s"') % values.get("code")
                            )
            res = (
                self.env["stock.inventory"]
                .with_context(ids=inventory_id)
                .prepare_inventory()
            )
            return res


class stock_inventory(models.Model):
    _inherit = "stock.inventory"

    @api.multi
    def action_start(self):
        if self._context.get("ids"):
            self = self._context.get("ids")
            for inventory in self:
                vals = {"state": "confirm", "date": fields.Datetime.now()}
                if (inventory.filter != "partial") and not inventory.line_ids:
                    vals.update(
                        {
                            "line_ids": [
                                (0, 0, line_values)
                                for line_values in inventory.line_ids
                            ]
                        }
                    )
                inventory.write(vals)
        else:
            super(stock_inventory, self).action_start()
        return True

    prepare_inventory = action_start
