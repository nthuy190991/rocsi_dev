// MULTIPLE CLICK TO AVOID FAST CLICKS TO BE COUNTED SEVERAL TIMES
var multipleClick_last_clickTime = null; 
var multipleClick_last_target = null; 

// AUDIO TO PLAY WHEN BUTTONS ARE CLICKED
var audio = new Audio('change_screen.ogg');

/*******************************************************************************
 * Quiz
 *************************************f*****************************************/  
var mauvaise_reponse = 0;
var nb_question = 0;
var nb_question_repondu = 0;
var new_nb_question_repondu = 0;
var button_is_actived = 0; // 0 => actif | 1 => non actif 

$(document).on('click','button.btn-quiz',function(e) {
	if(document.getElementsByClassName("question-deja-repondu").length==0) {
	    if(button_is_actived == 0 && $(this).parent().parent().find('.bouton-vrai').size()==0) {
			if($(this).hasClass('vrai')){
				$(this).addClass('bouton-vrai');
				session.raiseEvent("QuizzApp/Vrai");
			} else{
	            //Il ne faut incrementer le nombre de mauvaises reponses 
	            //que si on n'avait pas deja fait de reponse fausse a cette question
	            // Il ne faut ajouter la classe bouton-faux que si l'element ne l'a pas deja
				if(!$(this).hasClass('bouton-faux')){
	                if($(this).parent().parent().find('.bouton-faux').size()==0) {
	                    mauvaise_reponse++;
						session.raiseEvent("QuizzApp/Faux");
	                }    
	                $(this).addClass('bouton-faux');
	            }
	        }
	        
	        //On va tagger le conteneur question-reponse courant de la classe deja-repondu si ce n'est pas deja le cas
	        if(!$(this).parent().parent().hasClass('question-deja-repondu')){
	           $(this).parent().parent().addClass('question-deja-repondu');
	        }

		}    
	} 

});

// les questions au format json
var questions = null;
// question id courrant
var currantQuestionId = null;
// nombre de questions
var nbQuestions = null;

function preventMultipleClick(id) { 
    var preventClick = false;
    var currentClickTime = new Date(); 
    if (currentClickTime - multipleClick_last_clickTime < 500 && id == multipleClick_last_target) {
        preventClick = true; 
    } 
    multipleClick_last_target = id; 
    multipleClick_last_clickTime = currentClickTime; 
    return preventClick; 
}

function cleanerStr(text) {
	text = text.replace(/\\pau=1000\\/gi, "");
	text = text.replace(/réponse ./gi, "");
	return text.trim();
}

function loadJson(quizz_id) {
	$.getJSON( "json/quizz_" + quizz_id + ".json", function(data) {
		questions = data;
		currantQuestionId = 0;
		nbQuestions = Object.keys(questions).length;

		generateQuestionHtml(currantQuestionId); 
		sendQuestionToRobot(currantQuestionId);

	}).fail(function() {
    	console.error("Parsing error");
		session.raiseEvent("QuizzApp/ErreurJson", "Parsing error");
  	});
}

function sendQuestionToRobot(questionId) {
	var data = questions[questionId].question ;
	var rep = null;

	$.each(questions[questionId].reponse, function(i, item) {
		data += "\\pau=1000\\ " + item + " ";

		var rep = item.replace(/\\pau=1000\\/gi, "");
		rep = rep.replace(/réponse ./gi, "");
		var index = i;
		var listerep = [];
		listerep.push(cleanerStr(item));
		
		// mes à jour le concept dynamique (rep0, rep1, rep2) du dialogue 
		// attention obligation d'envoyer une liste
		session.service("ALDialog").then( function(proxy) {
			console.log(listerep);
			proxy.setConcept("rep" + index, "frf", listerep);
		});
	});
	session.raiseEvent("QuizzApp/Question", data);
}

function generateLogoHtml() {
	var html = "<div class='logo'></div>"
		+"<div class='textAcceuil'>"
		+	"<h1>QUIZZ</h1>"
		+	"<p>Veux-tu jouer avec moi ?</p>"
		+"</div>";

	$("#conteneur_questions").empty();
	$("#conteneur_questions").html(html);
};

function generateQuestionHtml(questionId) {
	var currantQuestion = questions[questionId].question;
	var currantResponses = questions[questionId].reponse;
	var currantClass = questions[questionId].clazz;
	var html = "<div class='conteneur_question_reponses' id='question_" + questionId + "'>"
		+ "<div class='conteneur_titre_quiz'><span>" + cleanerStr(currantQuestion) + "</span></div>"
		+ "<div class='conteneur_btn_quiz'><button class='btn-quiz " + currantClass[0] + "' id='a'>a</button><span class='conteneur_reponse'>" + cleanerStr(currantResponses[0]) + "</span></div>"
		+ "<div class='conteneur_btn_quiz'><button class='btn-quiz " + currantClass[1] + "' id='b'>b</button><span class='conteneur_reponse'>" + cleanerStr(currantResponses[1]) + "</span></div>"
		+ "<div class='conteneur_btn_quiz'><button class='btn-quiz " + currantClass[2] + "' id='c'>c</button><span class='conteneur_reponse'>" + cleanerStr(currantResponses[2]) + "</span></div>"
	+"</div>";

	$("#conteneur_questions").empty();
	$("#conteneur_questions").html(html);
};

function generateScoreHtml(nbMauvaiseReponse) {
	var score = Math.round((100 * (nbQuestions - nbMauvaiseReponse)) / nbQuestions);

	var eventToRobot = null;
	var html = "<div class='conteneur_question_reponses'>"
		+ "<div class='conteneur_titre_quiz'><span> Votre score est de : </span></div>";

	if (score < 26) {
		html += "<div class='resultat violet'><div class='score'>" + score + " %</div></div>";
		eventToRobot = "x";
	} else if (score < 51) {
		html += "<div class='resultat rouge'><div class='score'>" + score + " %</div></div>";
		eventToRobot = "xx";
	} else if (score < 76) {
		html += "<div class='resultat orange'><div class='score'>" + score + " %</div></div>";
		eventToRobot = "xxx";
	} else if (score < 100) {
		html += "<div class='resultat vert'><div class='score'>" + score + " %</div></div>";
		eventToRobot = "xxxx";
	} else {
		html += "<div class='resultat bleu'><div class='score'>" + score + " %</div></div>";
		eventToRobot = "xxxxx";
	}
	html +="</div>";

	$("#conteneur_questions").empty();
	$("#conteneur_questions").html(html);

	session.raiseEvent("QuizzApp/" + eventToRobot, score);
};

// APPLICATION SPECIFIC
// Events call backs


session.subscribeToEvent("QuizzApp/ShowLogo", function(quizzId) {
	generateLogoHtml();
});

session.subscribeToEvent("QuizzApp/QuizzId", function(quizzId) {
	loadJson(quizzId);
});

// Récupére l'evenement lorsque l'utilisateur répond en vocal à la question
session.subscribeToEvent("QuizzApp/Reponse", function(idButton) {
	document.getElementById(idButton).click();
});

session.subscribeToEvent("QuizzApp/Next", function() {
	if(currantQuestionId < (nbQuestions - 1)) {
		currantQuestionId ++;
		generateQuestionHtml(currantQuestionId);
		sendQuestionToRobot(currantQuestionId);
	} else {
		generateScoreHtml(mauvaise_reponse);
	}

});
    
$(document).ready(function(){
    // Button Exit action
    $('#btn_quit').click(function(){
        if (preventMultipleClick("Exit")) return;
        audio.play();
        session.raiseEvent("QuizzApp/Exit", true);
    });

    //TODO pour faire des tests
    //loadJson("1");

    // Lance l'evenement pour démmarer le dialogue
	session.raiseEvent("QuizzApp/Ready", "ready");
});