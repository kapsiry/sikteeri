/**
 * Initializes member list items to be used by detail showing and cart code.
 */
function enhanceMemberItem (item) {
    // Container for item functions like show details and add to cart
    item.buttons = $("<div>");
    item.buttons.css("display", "inline");
    item.append(item.buttons);

    // Container for member details
    item.memberDetails = $("<div>");
    item.append(item.memberDetails);
    item.memberDetails.hide();

    return item;
}


/**
 * A caching AJAX helper for fetching member details.
 */
var memberDetailStore = {};
function getMemberDetails (id, callbackFunction) {
    if (memberDetailStore[id] === undefined) {
	jQuery.post("handle_json/", '{"requestType": "MEMBERSHIP_DETAIL", "payload": ' + id + '}',
                    function(){return function(data){memberDetailStore[id]=data;callbackFunction(id);}}());
    }
    else {
	callbackFunction(id);
    }
}


/**
 * Creates membership detail objects.
 */
function makeMembershipDetailObject(id) {
    var obj = $("<div>").addClass("membership_details");
    obj.table = $("<table>").addClass("infobox");
    obj.title = $("<a>").html(gettext("Membership details")).addClass("member_detail_title");
    obj.title.click(function(){return function(){obj.table.slideToggle();}}());
    obj.append(obj.title);
    obj.append(obj.table);

    obj.populate = function(obj) {
	var data = $(memberDetailStore[id]);
	obj.table.html("");

	function addRow (elem, title, key) {
	    if (key == 'aliases') {
		console.log(typeof data.attr(key))
		console.log(data.attr(key))
	    }
	    var rowElem = $("<tr>").addClass("table_row");
	    rowElem.append($("<td>").html(title).addClass("key_column"));
	    rowElem.append($("<td>").html(data.attr(key)).addClass("value_column"));
	    elem.append(rowElem);
	}
	addRow(obj.table, gettext("Type"), "type");
	addRow(obj.table, gettext("Status"), "status");
	addRow(obj.table, gettext("Created"), "created");
	addRow(obj.table, gettext("Last changed"), "last_changed");
	addRow(obj.table, gettext("Home municipality"), "municipality");
	addRow(obj.table, gettext("Nationality"), "nationality");
	addRow(obj.table, gettext("Visible in the public memberlist"), "public_memberlist");
	addRow(obj.table, gettext("Aliases"), "aliases");
	addRow(obj.table, gettext("Additional information"), "extra_info");
    }
    return obj;
}

/**
 * Translates contact types to human-readable text.
 */
function translateContactType (text) {
    var dict = {};
    dict["person"] = gettext("Person contact");
    dict["billing_contact"] = gettext("Billing contact");
    dict["tech_contact"] = gettext("Technical contact");
    dict["organization"] = gettext("Organization");
    return dict[text];
}

/**
 * Creates contact detail objects.
 */
function makeContactDetailObject (id, type) {
    var obj = $("<div>").addClass("contact_details").addClass(type + "_contact_details");
    obj.table = $("<table>").addClass("infobox");
    obj.title = $("<a>").html(translateContactType(type)).addClass("member_detail_title");

    obj.title.click(function(){return function(){obj.table.slideToggle();}}());
    obj.append(obj.title);
    obj.append(obj.table);

    obj.populate = function(obj, type) {
	var data = $(memberDetailStore[id]["contacts"][type]);
	obj.table.html("");
	// If postal code is not specified, don't show -- most probably an empty object
	if ($(data).attr("postal_code") === undefined) {
	    return false;
	}

	function addRow (elem, title, key) {
            if ($(data).attr(key) === undefined || $(data).attr(key) == "") {
		return
	    }
	    var rowElem = $("<tr>").addClass("table_row");
	    rowElem.append($("<td>").html(title).addClass("key_column"));
	    rowElem.append($("<td>").html(data.attr(key)).addClass("value_column"));
	    elem.append(rowElem);
	}
	addRow(obj.table, gettext("First name"), "first_name");
	addRow(obj.table, gettext("Given names"), "given_names");
	addRow(obj.table, gettext("Last name"), "last_name");
	addRow(obj.table, gettext("Organization name"), "organization_name");
	addRow(obj.table, gettext("Street address"), "street_address");
	addRow(obj.table, gettext("Postal code"), "postal_code");
	addRow(obj.table, gettext("Post office"), "post_office");
	addRow(obj.table, gettext("Country"), "country");
	addRow(obj.table, gettext("Phone number"), "phone");
	addRow(obj.table, gettext("SMS number"), "sms");
	addRow(obj.table, gettext("E-mail"), "email");
	addRow(obj.table, gettext("Homepage"), "homepage");
	return true;
    }
    return obj;
}

/**
 * Creates the event list object.
 */
function makeMembershipEventsObject (id) {
    var obj = $("<div>").addClass("membership_events");
    obj.table = $("<table>").addClass("infobox");
    obj.title = $("<a>").html(gettext("Events")).addClass("member_detail_title");

    obj.title.click(function(){return function(){obj.table.slideToggle();}}());
    obj.append(obj.title);
    obj.append(obj.table);

    obj.populate = function(obj) {
	var data = $(memberDetailStore[id]["events"]);
	obj.table.html("");
	if (data.length == 0) {
	    return false;
	}
	function addRow (elem, title, key) {
	    var rowElem = $("<tr>").addClass("table_row");
	    rowElem.append($("<td>").html(title).addClass("key_column"));
	    rowElem.append($("<td>").html(key).addClass("value_column"));
	    elem.append(rowElem);
	}
	for (var i=0; i<data.length;i++) {
	    var item = data[i];
	    addRow(obj.table, item["user_name"] + ": " + item["date"], item["text"]);
	}

	return true;
    }
    return obj;
}

/**
 * Initializes member list items for AJAX details.
 */
function addMemberDetails (item) {
    item.membershipDetails = makeMembershipDetailObject(item.attr("id"));
    item.memberDetails.append(item.membershipDetails);

    item.personContactDetails = makeContactDetailObject(item.attr("id"), "person");
    item.memberDetails.append(item.personContactDetails);

    item.billingContactDetails = makeContactDetailObject(item.attr("id"), "billing_contact");
    item.memberDetails.append(item.billingContactDetails);

    item.techContactDetails = makeContactDetailObject(item.attr("id"), "tech_contact");
    item.memberDetails.append(item.techContactDetails);

    item.organizationContactDetails = makeContactDetailObject(item.attr("id"), "organization");
    item.memberDetails.append(item.organizationContactDetails);

    item.membershipEvents = makeMembershipEventsObject(item.attr("id"));
    item.memberDetails.append(item.membershipEvents);

    item.viewDetailsButton = $("<a>").html(gettext("show details")).addClass("cart_function");
    item.buttons.append(item.viewDetailsButton);

    item.hideDetailsButton = $("<a>").html(gettext("hide details")).addClass("cart_function");
    item.buttons.append(item.hideDetailsButton);
    item.hideDetailsButton.hide();

    item.hideDetailsButton.click(
	function(){return function(){
		       item.memberDetails.slideUp();
                       item.hideDetailsButton.hide();
                       item.viewDetailsButton.show();}
		  }());

    function callbackFactory() {
	return function () {
	    getMemberDetails(item.attr("id"),
			     function(){
				 return function(){
				     item.membershipDetails.populate(item.membershipDetails);
				     if (!item.personContactDetails.populate(item.personContactDetails, "person")) {
					 item.personContactDetails.hide();
				     }
				     if (!item.billingContactDetails.populate(item.billingContactDetails, "billing_contact")) {
					 item.billingContactDetails.hide();
				     }
				     if (!item.techContactDetails.populate(item.techContactDetails, "tech_contact")) {
					 item.techContactDetails.hide();
				     }
				     if (!item.organizationContactDetails.populate(item.organizationContactDetails, "organization")) {
					 item.organizationContactDetails.hide();
				     }
				     if (!item.membershipEvents.populate(item.membershipEvents)) {
					 item.membershipEvents.hide();
				     }
				     item.memberDetails.slideDown();
				     item.viewDetailsButton.hide();
				     item.hideDetailsButton.show();}}());
	}
    }
    item.viewDetailsButton.click(callbackFactory());

    return item;
}


/**
 * Makes member list items work with preapprove-cart.
 */
function preapproveify (item) {
    var id = item.attr("id");

    item.addButton = $("<a>").html(gettext("add to pre-approve cart")).addClass("cart_function");
    item.buttons.append(item.addButton);

    item.removeButton = $("<a>").html(gettext("remove from pre-approve cart")).addClass("cart_function");
    item.buttons.append(item.removeButton);
    item.removeButton.hide();

    item.addButton.click(function(){
			     return function(){$("#preapprovable_cart").append(item);
                                               item.addButton.hide();
                                               item.removeButton.show();}}());
    item.removeButton.click(function(){
				return function(){$("#memberlist").append(item);
						  item.removeButton.hide();
						  item.addButton.show();}}());
}


/**
 * Makes member list items work with approve-cart.
 */
function approveify (item) {
    var id = item.attr("id");

    item.addButton = $("<a>").html(gettext("add to approve cart")).addClass("cart_function");
    item.buttons.append(item.addButton);

    item.removeButton = $("<a>").html(gettext("remove from approve cart")).addClass("cart_function");
    item.buttons.append(item.removeButton);
    item.removeButton.hide();

    item.addButton.click(function(){
			     return function(){$("#approvable_cart").append(item);
                                               item.addButton.hide();
                                               item.removeButton.show();}}());
    item.removeButton.click(function(){
				return function(){$("#memberlist").append(item);
						  item.removeButton.hide();
						  item.addButton.show();}}());
}
