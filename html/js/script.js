session.subscribeToEvent("FacialRecognition/name", function(name) {
	console.log(name);
	// alert(name);
	show_photos(name);
});

session.subscribeToEvent("FacialRecognition/videoStreaming", function() {
	console.log('video');
	// alert('video');
	show_video();
});

session.subscribeToEvent("FacialRecognition/videoFormation", function(filename) {
	// alert('video');
	// if (filename === 'STOP'){
	// 	console.log('Stop la video');
	// 	// hide_video();
	// 	window.setTimeout(function(){hide_video();}, 2000)
	// }
	// else{
	console.log('video indication la salle ' + filename);
	play_video(filename);
	// }
});

session.subscribeToEvent("FacialRecognition/tts", function(text) {
	console.log('Bot: '+text);
	if (text!== ''){
		bot_say(text);
	}
});

session.subscribeToEvent("FacialRecognition/stt", function(text) {
	console.log('Human: '+text);
	if (text!== ''){
		human_say(text);
	}
});

session.subscribeToEvent("Banque/tts", function(text) {
	console.log('Bot: '+text);
	bot_say(text);
});

session.subscribeToEvent("Banque/stt", function(text) {
	console.log('Human: '+text);
	human_say(text);
});

session.subscribeToEvent("Telco/tts", function(text) {
	console.log('Bot: '+text);
	bot_say(text);
});

session.subscribeToEvent("Telco/stt", function(text) {
	console.log('Human: '+text);
	human_say(text);
});

session.subscribeToEvent("FacialRecognition/quit", function(quit) {
	console.log('Quit...');
	au_revoir();
});

function show_photos(name) {
		if (name !== ""){
			var firstLetter = name[0].toUpperCase();
			$('h1.bonjour').html("Bonjour " + firstLetter.concat(name.substring(1)) + " !");
			$('center.images').empty();
			var names = [name+'.0', name+'.1', name+'.2', name+'.3', name+'.4'];

			$.ajax({
					url:'face_database_pepper/' + names[0] + '.png',
					type:'HEAD',
					error: function()
					{
						$('h2.text').html("<b>Veuillez patienter...</b>");
					},
					success: function()
					{
						$.each(names, function(index) {
							$('h2.text').html('<b>Vos photos prises :</b>');
							$('center.images').append('&emsp; <img src="face_database_pepper/' + this + '.png?t=' + new Date().getTime() + '"  alt="photo'+index+'"  style="width:200px;">');
						});
					}
			});
		}
		else { // if (name=='')
			$('h2.text').html("<b>Les photos sont en train d'être prises. Veuillez patienter...</b>");
			$('h1.bonjour').html("Bonjour !");
			$('center.images').empty();
		}
}

function show_video(){
	$('center.video img').attr('src', 'out.png?t=' + new Date().getTime());
}


function bot_say(text){
	var text2 = '&nbsp;<b style="color:#FF0000">Moi:</b>&nbsp;&nbsp;&nbsp;' + text + '<br>';
	$('div.conversation').append(text2);
	scrollToBottom();
}

function human_say(text){
	var text2 = text[0].toUpperCase(); // Put first letter on uppercase
	var text3 = '&nbsp;<b style="color:#0000FF">Vous:</b>&nbsp;' + text2.concat(text.substring(1)) + '<br>';
	$('div.conversation').append(text3);
	scrollToBottom();
}

function play_video(filename){
	$('center.images').hide();
	// var html = '<video id="formVideo" controls="controls" width="800" preload="auto" autoplay loop><source src="video/' + filename + '.mp4" type="video/mp4"></video>';
	var html = '<video id="formVideo" controls="controls" width="800" preload="auto" autoplay loop><source src="http://192.168.1.11//apps/ocformationapp-e2d3ee/video/'+filename+'.mp4" type="video/mp4"></video>';
	$('center.video').empty();
	$('center.video').append(html);
	// $('center.video').show();
}

function hide_video(){
	$('center.video').hide();
}

function au_revoir() {
		$('h2.text').html("<b>Le programme a été lancé pendant 20 minutes. C'est l'heure pour se reposer.</b>");
		$('h1.bonjour').html("A très bientôt");
		$('center.images').empty();
		$('center.images').append('<br> <img src="img/aurevoir2.jpg" alt="photo"  style="width:800px;">');
		//$('div.conversation').empty();
}


function scrollToBottom (){
      $('.conversation').animate({ scrollTop: $('.conversation').prop("scrollHeight") + 'px' }, 1000);
}

// initial load
$(document).ready(function() {
	// show_photos("nouvelle personne");
	// play_video('407');
	// window.setTimeout(function(){hide_video();}, 5000)
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
	// bot_say("bonjour");
	// human_say("bonjour pepper");
});
