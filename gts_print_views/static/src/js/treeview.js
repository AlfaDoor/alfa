odoo.define('web_export_view_new', function (require) {
"use strict";

    var core = require('web.core');
    var Sidebar = require('web.Sidebar');
    var session = require('web.session');
    var crash_manager = require('web.crash_manager');
    var rpc = require('web.rpc');
    var Dialog = require('web.Dialog');

    var QWeb = core.qweb;

    var _t = core._t;
    var value_list = []
    Sidebar.include({

        _redraw: function () {
            var self = this;
            this._super.apply(this, arguments);
            if (self.getParent().renderer.viewType == 'list') {
                session.user_has_group('web_export_view.group_disallow_export_view_data_excel').then(function (has_group) {
                    if (!has_group) {
                        self.$el.find('.o_dropdown').last().append(QWeb.render('WebExportTreeViewPDF', { widget: self }));
                         self.$el.find('.export_treeview_pdf').on('click', self.on_sidebar_export_treeview_xls);
                    }
                });
            }
        },

        on_sidebar_export_treeview_xls: function () {
          var self = this,
            // Select the first list of the current (form) view
            // or assume the main view is a list view and use that
            view = this.getParent(),
            children = view.getChildren();
             var dialog = new Dialog(document.body, {
                title: "Add the Quotes For Report",
                subtitle: "",
                size: 'medium',
                  $content: $('<div>',
                    {
                        html: QWeb.render('DialogMessage'),
                    }),
                buttons: [],
                });
                dialog.opened().then(function () {
                     var self = this;
                     dialog.$('.o_event_pdf_button').on('click', function (e) {
                        value_list.push($('#hero-demo').val())

                        var c = crash_manager;
                        if ((value_list.length) >0)
                        {
                        if (children) {
                            children.every(function (child) {
                                if (child.field && child.field.type == 'one2many') {
                                    view = child.viewmanager.views.list.controller;
                                    return false; // break out of the loop
                                }
                                if (child.field && child.field.type == 'many2many') {
                                    view = child.list_view;
                                    return false; // break out of the loop
                                }
                                return true;
                            });
                        }
                    var export_columns_keys = [];
                    var export_columns_names = [];
                    var column_index = 0;
                    var column_header_selector;
                    $.each(view.renderer.columns, function () {
                        if (this.tag == 'field' && (this.attrs.widget === undefined || this.attrs.widget != 'handle')) {
                            // non-fields like `_group` or buttons
                            export_columns_keys.push(column_index);
                            column_header_selector = '.o_list_view > thead > tr> th:not([class*="o_list_record_selector"]):eq('+column_index+')';
                            export_columns_names.push(view.$el.find(column_header_selector)[0].textContent);
                        }
                        column_index ++;
                    });
                    var export_rows = [];
                    $.blockUI();
                    if (children) {
                        // find only rows with data
                        view.$el.find('.o_list_view > tbody > tr.o_data_row:has(.o_list_record_selector input:checkbox:checked)')
                        .each(function () {
                            var $row = $(this);
                            var export_row = [];
                            $.each(export_columns_keys, function () {
                                var $cell = $row.find('td.o_data_cell:eq('+this+')')
                                var $cellcheckbox = $cell.find('.o_checkbox input:checkbox');
                                if ($cellcheckbox.length) {
                                    export_row.push(
                                        $cellcheckbox.is(":checked")
                                        ? _t("True") : _t("False")
                                    );
                                }
                                else {
                                    var text = $cell.text().trim();
                                    var is_number = (
                                        $cell.hasClass('o_list_number') &&
                                        !$cell.hasClass('o_float_time_cell')
                                    );
                                    if (is_number) {
                                        export_row.push(parseFloat(
                                            text
                                            // Remove thousands separator
                                            .split(_t.database.parameters.thousands_sep)
                                            .join("")
                                            // Always use a `.` as decimal separator
                                            .replace(_t.database.parameters.decimal_point, ".")
                                            // Remove non-numeric characters
                                            .replace(/[^\d\.-]/g, "")
                                        ));
                                    } else {
                                        export_row.push(text);
                                    }
                                }
                            });
                            export_rows.push(export_row);
                        });
                    }
                    var pdfsize = 'a4';
                    var doc = new jsPDF('l', 'pt', pdfsize);
                  rpc.query({
                        model: 'res.company',
                        method: 'all_company_data',
                        args: [[self.id]],

                    })
                    .then(function (result) {
                        // Preparing Header
                        var header = function(data) {
                            if (result['format_type'] == 'A'){
                                var pageSize = doc.internal.pageSize;
                                doc.setFontSize(16);
                                doc.setTextColor(40);
                                var headerImgData = "data:image/png;base64," + result['logo'];
                                doc.addImage(headerImgData, 'JPEG', 30, 30, 150, 60);
                                doc.setFontType("bold");
                                doc.text(510, 30, result['name']);
                                doc.setFontStyle('normal');
                                doc.setFontSize(13);
                                if (result['complete_street'] !== undefined){
                                    doc.text(510, 48, result['complete_street']);
                                }
                                if (result['remaining_address'] !== undefined){
                                    doc.text(510, 66, result['remaining_address']);
                                }
                                if (result['phone'] !== undefined){
                                    doc.text(510, 84, 'Tel: ' + result['phone']);
                                }
                                if (result['email'] !== undefined){
                                    doc.text(510, 102, result['email']);
                                }
                                // Line
                                doc.setLineWidth(1.5); // #a24689
                                doc.setDrawColor(162, 70, 137);
                                doc.line(30, 110, pageSize.width - 30, 110);
                                doc.setFontSize(16);
                                // Message
                                var message = $('#hero-demo').val()
                                var xOffset = (pageSize.width / 2) -
                                    (doc.getStringUnitWidth(message) * doc.internal.getFontSize() / 2);
                                doc.text(xOffset, 130, message);
                                // FOOTER
                                var totalPagesExp = "{total_pages_count_string}";
                                var str = "Page " + data.pageCount;
                                if (typeof doc.putTotalPages === 'function') {
                                    str = str
                                }
                                doc.line(30, pageSize.height - 45, pageSize.width - 30, pageSize.height - 45);
                                doc.setFontSize(13);
                                doc.text(str, 745, pageSize.height - 32);
                                if (result['vat'] !== undefined){
                                    doc.text('Vat/GSTIN : ' + result['vat'], 30, pageSize.height - 32);
                                }
                                if (result['website'] !== undefined){
                                    doc.text(result['website'], 30, pageSize.height - 15);
                                }
                                doc.text('', 510, pageSize.height - 32);
                                doc.text('', 510, pageSize.height - 13);
                            };
                        };

                        var options = {
                            beforePageContent: header,
                            startY: doc.previousAutoTable.finalY,
                            margin: {
                              top: 65,
                              bottom: 65,
                            },
                        };
                    doc.setFontSize(10);
                    // Or JavaScript:
                    doc.autoTable({
                        beforePageContent: header,
                        head: [export_columns_names],
                        body: export_rows,
                        theme:'grid',
                        startY: 140,
                        margin: {
                            top: 140,
                            left: 30,
                            right: 30,
                        },
                       overflowColumns: false

                    });
                        doc.save('Tree_view.pdf')
                        window.location.reload();
                        });

                        }
                     });
                      dialog.$('.button_cancel').on('click', function (e) {
                        dialog.close();
                      });
                     });
                dialog.open()
        }

    });

});
