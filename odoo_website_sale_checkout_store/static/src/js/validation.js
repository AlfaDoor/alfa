odoo.define('odoo_website_sale_checkout_store.form_validation', function(require){
	'use strict';

	$(document).ready(function(){

		var pickup_type = $(".pickup_type").val();

		if(['paynow_delivery','payon_delivery'].includes(pickup_type)){
			$('.oe_website_sale .country_id').on('change', function(){
				var country_id = $('.country_id').find(":selected").attr('value');
				if($('#country_id').val() != 'Country...') {
					$(".state").each(function( index ) {
						if($(this).attr('country') != country_id){
							$(this).hide();
						}else{
							$(this).show();
						}
					});
				}
			});

			$('#state_id').hide(); 
			$('#country_id').change(function(){
				if($('#country_id').val() == 'Country...') {
					$('#state_id').hide(); 
				} else {
					$('#state_id').show(); 
				} 
			});

		}

		
		
		$( "#o_checkout_confirm" ).click(function() {
			var name = $(".checkout_name").val();
			var email = $(".checkout_email").val();
			var phone = $(".checkout_phone").val();
			var city = $(".city").val();
			var street = $(".street").val();
			var state_id = $(".state_id").val();
			var country_id = $(".country_id").val();

			if(!name){
				$(".checkout_name").val('');
				$(".checkout_name").css("border-bottom-color", "red");
				alert('Please add name.');
				setTimeout(function() {
					$(".checkout_name").css("border-bottom-color", "#ced4da");
				},2000);
			}
			else if(!email){
				$(".checkout_email").val('');
				$(".checkout_email").css("border-bottom-color", "red");
				alert('Please add email.');
				setTimeout(function() {
					$(".checkout_email").css("border-bottom-color", "#ced4da");
				},2000);
			}
			else if(email && !isValidEmailAddress(email)){
				$(".checkout_email").val('');
				$(".checkout_email").css("border-bottom-color", "red");
				alert('Invalid Email Address.');
				setTimeout(function() {
					$(".checkout_email").css("border-bottom-color", "#ced4da");
				},2000);
			} 
			else if(!phone){
				$(".checkout_phone").val('');
				$(".checkout_phone").css("border-bottom-color", "red");
				alert('Please add phone number.');
				setTimeout(function() {
					$(".checkout_phone").css("border-bottom-color", "#ced4da");
				},2000);                    
			}
			else {
				if(['paynow_delivery','payon_delivery'].includes(pickup_type)){
					if(!street){
						$(".street").val('');
						$(".street").css("border-bottom-color", "red");
						alert('Please add street.');
						setTimeout(function() {
							$(".street").css("border-bottom-color", "#ced4da");
						},2000);                    
					}
					else if(!city){
						$(".city").val('');
						$(".city").css("border-bottom-color", "red");
						alert('Please add city.');
						setTimeout(function() {
							$(".city").css("border-bottom-color", "#ced4da");
						},2000);                    
					}
					else if(!country_id){
						$(".country_id").val('');
						$(".country_id").css("border-bottom-color", "red");
						alert('Please select country.');
						setTimeout(function() {
							$(".country_id").css("border-bottom-color", "#ced4da");
						},2000);                    
					}
					else{

					}
				}
			
			}

		});


		function isValidEmailAddress(emailAddress) {
			var pattern = new RegExp(/^(("[\w-\s]+")|([\w-]+(?:\.[\w-]+)*)|("[\w-\s]+")([\w-]+(?:\.[\w-]+)*))(@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,6}(?:\.[a-z]{2})?)$)|(@\[?((25[0-5]\.|2[0-4][0-9]\.|1[0-9]{2}\.|[0-9]{1,2}\.))((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[0-9]{1,2})\.){2}(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[0-9]{1,2})\]?$)/i);
			return pattern.test(emailAddress);
		}
	});
	
});