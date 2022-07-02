12.0.0.1--->index updated


12.0.0.2-->
1) Add new checkout option field to sale order, and for pickup option
add contact to pick order.
2) According to checkout option redirect to payment page or 
direct confirm order.

Version 12.0.0.3 : (20/04/20)
		- Hide all checkout buttons when any of configured boolean is true.
		- Solve issue and make sure all existing functionality works when nor of configured boolean is true.
		- Update forms for nonlogin user in odoo_website_sale_checkout_store in v13.
		- Change js code to jquery for better use.
		- Add Validations in forms.
		- Add country and state ,add validation for states also.
		- Solve issue of wrong order update.
		- Update address and confirm_order methods from main.py
		- Hide partner address when options are pickup at store at confirmation page
		- Show Company address and phone number when options are pickup at store 
		- Hide partner address when options are pickup at store at payment page
