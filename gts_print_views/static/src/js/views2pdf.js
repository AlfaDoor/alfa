odoo.define('gts_print_views2', function (require) {
        "use strict";
    var core = require('web.core');
    var PivotController = require('web.PivotController');
    var framework = require('web.framework');
    var CalendarController = require('web.CalendarController');
     var ListController = require('web.ListController');
    var FormController = require('web.FormController');
     var rpc = require('web.rpc');
    var Dialog = require('web.Dialog');

    var QWeb = core.qweb;

    ListController.include({
        // OVERRIDE 'web.ListController.renderButtons()'
        renderButtons: function ($node) {
            // APPLY SUPER
            this._super.apply(this, arguments);
            var self = this;
            // UPDATE HEADER BUTTONS
            if (this.$buttons) {
                // ADD EVENT LISTENER TO NEW 'PRINT' HEADER BUTTON
                this.$buttons.find('#create_pdf').on('click', function (event) {
                    event.preventDefault();
                    self.generatePDF();
                });
            }
        },
        // ADD NEW FUNCTION 'generatePDF()' TO 'web.ListController'
        generatePDF: function() {
            var form = $('.o_view_controller');
            var cache_width = form.width();
            var a4 = [800, 841.89];  // A4 PAPER SIZE
            // CREATE CANVAS OBJECT
            function getCanvas() {
                form.width((a4[0] * 1.33333) - 80).css('max-width', 'none');
                return html2canvas(form, {
                    imageTimeout: 2000,
                    removeContainer: true
                });
            }
            // CREATE PDF OBJECT
            function createPDF() {
                getCanvas().then(function (canvas) {
                    var img = canvas.toDataURL("image/png");
                    var doc = new jsPDF({
                        unit: 'px',
                        format: 'letter',
                        orientation: 'landscape'
                    });
                    var title = $('ol.breadcrumb').find('li.active').html();
                    doc.setFont("helvetica");
                    doc.setFontType("bold");
                    doc.setTextColor(0,0,255);
                    doc.text(title, 20, 30);
                    doc.addImage(img, 'JPEG', 20, 60);
                    doc.save('list.pdf');
                    form.width(cache_width);
                });
            }
            $('body').scrollTop(0);
            createPDF();
        },
    });

    // UPDATE 'web.FormController'
    FormController.include({
        // OVERRIDE 'web.FormController.renderButtons()'
        renderButtons: function($node) {
            // APPLY SUPER
            this._super.apply(this, arguments);
            var self = this;
            // UPDATE HEADER BUTTONS
            if (this.$buttons) {
                // ADD EVENT LISTENER TO NEW 'PRINT' HEADER BUTTON
                this.$buttons.on('click', '#create_pdf', function (event) {
                    event.preventDefault();
                    self.generatePDF();
                });
            }
        },
        // ADD NEW FUNCTION 'generatePDF()' TO 'web.FormController'
        generatePDF: function() {
            var form = $('.o_view_controller');
            var cache_width = form.width();
            var a4 = [800, 841.89];  // A4 PAPER SIZE
            // CREATE CANVAS OBJECT
            function getCanvas() {
                form.width((a4[0] * 1.33333) - 80).css('max-width', 'none');
                return html2canvas(form, {
                    imageTimeout: 2000,
                    removeContainer: true
                });
            }
            // CREATE PDF OBJECT
            function createPDF() {
                getCanvas().then(function (canvas) {
                    var img = canvas.toDataURL("image/png");
                    var doc = new jsPDF({
                        unit: 'px',
                        format: 'letter',
                        orientation: 'landscape'
                    });
                    var title = $('ol.breadcrumb').find('li.active').html();
                    doc.setFont("helvetica");
                    doc.setFontType("bold");
                    doc.setTextColor(0,0,255);
                    doc.text(title, 20, 30);
                    doc.addImage(img, 'JPEG', 20, 60);
                    doc.save('form.pdf');
                    form.width(cache_width);
                });
            }
            $('body').scrollTop(0);
            createPDF();
        },
    });

    // override PivotView

   PivotController.include({
        // OVERRIDE 'web.PivotController.renderButtons()'
        renderButtons: function($node) {
            // APPLY SUPER
            this._super.apply(this, arguments);
            var self = this;
            // UPDATE HEADER BUTTONS
            if (this.$buttons) {
                // ADD EVENT LISTENER TO NEW 'PRINT' HEADER BUTTON
                this.$buttons.on('click', '#create_pdf', function (event) {
                    var $target = $(event.target);
                    self._downloadTablePDF();
//

                });
            }
        },

         _downloadTablePDF: function () {
            var table = this.model.exportData();
            var list_head = []
            var pdfsize = 'a4';
            var doc = new jsPDF('l', 'pt', pdfsize);
            doc.page = 1; // use this as a counter.
            var self = this;
            // Preparing Table header
            var nbr_measures = table['nbr_measures'];
            var actual_measures = table['measure_row'].length;
            var header_list = [];
            var temp_dict = {}
            var temp_list = []
            for (var i = 0; i < table['headers'].length; i++) {
                temp_list = [{
                    content: "   ",
                    colSpan: 1,
                    styles: {halign: 'left'}
                }]
                for (var j = 0; j < table['headers'][i].length; j++) {
                    temp_dict = {
                        content: table['headers'][i][j]['title'].toString(),
                        colSpan: table['headers'][i][j]['width'],
                        styles: {halign: 'left'}
                    }
                    temp_list.push(temp_dict);
                }
                header_list.push(temp_list);
            }
            temp_list = [{
                content: "   ",
                colSpan: 1,
                styles: {halign: 'center'}
            }]
            for (var i = 0; i < table['measure_row'].length; i++) {
                temp_dict = {
                    content: table['measure_row'][i]['measure'].toString(),
                    colSpan: 1,
                    styles: {halign: 'center'}
                }
                temp_list.push(temp_dict);
            }
            header_list.push(temp_list);
            // Preparing table rows
            var answer_list = []
            for (i = 1; i < table['rows'].length; i++) {
                var answer_list2 = []
                var str = ''
                var len = 0;
                var space = ''
                if (table['rows'][i]['indent'] === 1){
                    str = '+' + table['rows'][i]['title'].toString()
                }
                if (table['rows'][i]['indent'] > 1){
                    str = '-' + table['rows'][i]['title'].toString()
                }

                if (table['rows'][i]['indent'] > 1){
                    len = str.length;
                    space = 4 * table['rows'][i]['indent'];
                }
                answer_list2.push(str.padStart(len + space, ' '))
                answer_list.push(answer_list2)
                for (var p = 0; p < table['rows'][i]['values'].length; p++) {
                    answer_list2.push(table['rows'][i]['values'][p]['value'].toString())
                }
            }

            // Code for dialog open
            var dialog = new Dialog(document.body, {
                title: "Report Header",
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
                        }
                        var options = {
                            beforePageContent: header,
                            startY: doc.previousAutoTable.finalY,
                            margin: {
                              top: 65,
                              bottom: 65,
                            },
                        };
                        doc.setFontSize(10);
                        // Calculating First column width
                        var first_column_width = 175
                        if (header_list.length > 9){
                            first_column_width = 95
                        }
                        else if (header_list.length > 8){
                            first_column_width = 120
                        }
                        // Printing Table
                        doc.autoTable({
                            beforePageContent: header,
                            head: header_list,
                            body: answer_list,
                            theme:'grid',
                            styles: {
                                // overflow: 'linebreak',
                                // columnWidth: 'wrap',
                                cellWidth: 'auto',
                                minCellWidth: 45
                            },
                            columnStyles: {
                                0: {
                                    cellWidth: first_column_width
                                },
                            },
                            startY: 140,
                            margin: {
                                top: 140,
                                left: 30,
                                right: 30,
                            },
                           overflowColumns: false
                        });
                        doc.save('Pivot_View.pdf')
                        window.location.reload();
                    });
                 });
                 dialog.$('.button_cancel').on('click', function (e) {
                    dialog.close();
                 });
            });
            dialog.open();
        },
    });


   CalendarController.include({
        // OVERRIDE 'web.CalendarController.renderButtons()'
        renderButtons: function($node) {
            // APPLY SUPER
            this._super.apply(this, arguments);
            var self = this;
            // UPDATE HEADER BUTTONS
            if (this.$buttons) {
                // ADD EVENT LISTENER TO NEW 'PRINT' HEADER BUTTON
                this.$buttons.on('click', '#create_pdf', function (event) {
                    event.preventDefault();
                    self.generatePDF();
                });
            }
        },
        // ADD NEW FUNCTION 'generatePDF()' TO 'web.CalendarController'
        generatePDF: function() {
            var form = $('.o_view_controller');
            var cache_width = form.width();
            var a4 = [800, 841.89];  // A4 PAPER SIZE
            // CREATE CANVAS OBJECT
            function getCanvas() {
                form.width((a4[0] * 1.33333) - 80).css('max-width', 'none');
                return html2canvas(form, {
                    imageTimeout: 2000,
                    removeContainer: true
                });
            }
            // CREATE PDF OBJECT
            function createPDF() {
                getCanvas().then(function (canvas) {
                    var img = canvas.toDataURL("image/png");
                    var doc = new jsPDF({
                        unit: 'px',
                        format: 'letter',
                        orientation: 'landscape'
                    });
                    var title = $('ol.breadcrumb').find('li.active').html();
                    doc.setFont("helvetica");
                    doc.setFontType("bold");
                    doc.setTextColor(0,0,255);
                    doc.text(title, 20, 30);
                    doc.addImage(img, 'JPEG', 20, 60);
                    doc.save('calendar.pdf');
                    form.width(cache_width);
                });
            }
            $('body').scrollTop(0);
            createPDF();
        },
    });

});