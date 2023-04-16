{
'name':'sale_restrictions',
'summary':'Restrict users to make sale order over a limit based on credit and days and also sale person can not change unit price without approval',
'author':'SIT & think digital',
'depends':['base','sale','purchase','account','alfa_customizations'],
'data':[
        'security/final_approval.xml',
        'view/credit_day_limit.xml'],
'category' : 'Custom',
'website' : "sitco.odoo.com",
'installable' : True,
'auto_install' : False,
}
