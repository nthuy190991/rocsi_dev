/*eslint-env jquery, browser*/
/*globals webkitSpeechRecognition */
'use strict';

var audioQueue = [];
var audio = $('.audio').get(0);

var isChrome = !!window.chrome && !!window.chrome.webstore;

var $dialogsLoading = $('.dialogs-loading');

// conversation nodes
var $conversation = $('.conversation-container');
var $userInput = $('.user-input');

var clientid = -1;

// initial load
$(document).ready(function() {
	clientid = Math.floor(Math.random() * 1000000000 + 1);
	$.post('/start?id='+clientid);

	// $.post('/start');
	waitForServerInput();
});

function waitForServerInput() {
	$.post('/wait?id='+clientid).done(function(data) {
		waitForServerInput();
		if (data !== ""){
			if (data.indexOf("Human") === 0) {
				var txt = data.substring(8);
				displayHumanChat(txt);
			}
			else if (data.indexOf("Bot") === 0) {
				var txt = data.substring(6);
				if (txt!==""){
					displayBotChat(txt);
				}
			}
		}
	});
}

function displayBotChat(text) {
	$('<div class="bubble-watson"/>').html(text).appendTo($conversation);
	scrollToBottom();
	$dialogsLoading.hide();
}

function displayHumanChat(text) {
    $('<p class="bubble-human"/>').html(text)
        .appendTo($conversation);
    $('<div class="clear-float"/>')
        .appendTo($conversation);
    scrollToBottom();
		$dialogsLoading.show();
}

// function scrollToBottom (){
//     $('body, html').animate({ scrollTop: $('body').height() + 'px' });
// }
function scrollToBottom (){
    $('body, html').animate({ scrollTop: $('body').prop("scrollHeight") + 'px' }, 1000);
}
