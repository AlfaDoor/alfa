odoo.define('basic_hr.SaveReadonly', function (require) {
    'use strict';

    var BasicModel = require('web.BasicModel');

    BasicModel.include({
        _isFieldProtected: function (record, fieldName, viewType) {
            return false;
        }
    })
});
