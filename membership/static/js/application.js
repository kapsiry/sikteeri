/**
 * A caching availability checker for alias availability
 */
var aliasAvailability = {};
function aliasAvailable (alias, callbackFunction) {
    if (aliasAvailability[alias] === undefined) {
	jQuery.post("handle_json/", '{"requestType": "ALIAS_AVAILABLE", "payload": "' + alias + '"}',
                    function(){
			return function(data){
			    if (data == 'true') {
				aliasAvailability[alias] = true;
			    }
			    else if (data == 'false') {
				aliasAvailability[alias] = false;
			    }
			    callbackFunction(aliasAvailability[alias]);
			}
		    }());
    }
    else {
	callbackFunction(aliasAvailability[alias]);
    }
}

function cleanAccents (s) {
    var r=s.toLowerCase();
    r = r.replace(new RegExp("\\s", 'g'),"");
    r = r.replace(new RegExp("[àáâãäå]", 'g'),"a");
    r = r.replace(new RegExp("æ", 'g'),"ae");
    r = r.replace(new RegExp("ç", 'g'),"c");
    r = r.replace(new RegExp("[èéêë]", 'g'),"e");
    r = r.replace(new RegExp("[ìíîï]", 'g'),"i");
    r = r.replace(new RegExp("ñ", 'g'),"n");                            
    r = r.replace(new RegExp("[òóôõö]", 'g'),"o");
    r = r.replace(new RegExp("œ", 'g'),"oe");
    r = r.replace(new RegExp("[ùúûü]", 'g'),"u");
    r = r.replace(new RegExp("[ýÿ]", 'g'),"y");
    r = r.replace(new RegExp("\\W", 'g'),"");
    return r;
};

function generateEmailForwards (firstName, givenNames, lastName) {
    var firstName = cleanAccents(firstName);
    var givenNames = givenNames.split(" ");
    for (var i=0; i<givenNames.length; i++) {
	givenNames[i] = cleanAccents(givenNames[i]);
    }
    var lastName = cleanAccents(lastName);

    var permutations = [];
    permutations.push(firstName + "." + lastName);
    permutations.push(lastName + "." + firstName);
    
    var nonFirstNames = [];
    var initials = [];
    $.each(givenNames, function (idx, val) {
	if (val !== undefined && val != firstName) {
	    nonFirstNames.push(val);
	    initials.push(val[0]);
	}
    });

    if (initials.length > 0) {
	permutations.push(firstName + "." + initials[0] + "." + lastName);
	permutations.push(initials[0] + "." + firstName + "." + lastName);
    }
    return permutations;
}

