$(document).ready(function(){

	$('.posts').on('click', 'li .vote-section .upvote', function(){
		$.ajax({
			url: '/upvote/post/' + $(this).attr('id'),
			type: 'post',
			contentType: 'application/json',
			data: JSON.stringify({
				id: $(this).attr('id')
			}),
			success: function(response){
				if (response.redirect){
					window.location.href = response.redirect;
				}
				else {
					var vote_section = $('.posts').children(''.concat('#', response.id))
						.children('.vote-section').eq(0);
					vote_section.children(''.concat('#post', response.id, 'vote-count')).text(response.data);
					var upvote_btn = vote_section.children('.upvote');
					var downvote_btn = vote_section.children('.downvote');
					switch (response.status) {
						case 'UP':
							upvote_btn.css('color', '#c64600');
							downvote_btn.css('color', '#9a9996');
							break;
						default:
							upvote_btn.css('color', '#9a9996');
					}
				}
			}
		})
	})

	$('.posts').on('click', 'li .vote-section .downvote', function(){
		$.ajax({
			url: '/downvote/post/' + $(this).attr('id'),
			type: 'post',
			contentType: 'application/json',
			data: JSON.stringify({
				id: $(this).attr('id')
			}),
			success: function(response){
				if (response.redirect){
					window.location.href = response.redirect;
				}
				else {
					var vote_section = $('.posts').children(''.concat('#', response.id))
						.children('.vote-section').eq(0);
					var upvote_btn = vote_section.children('.upvote');
					var downvote_btn = vote_section.children('.downvote');
					vote_section.children(''.concat('#post', response.id, 'vote-count')).text(response.data);

					switch (response.status) {
						case 'DOWN':
							upvote_btn.css('color', '#9a9996');
							downvote_btn.css('color', '#003399');
							break;
						default:
							downvote_btn.css('color', '#9a9996');
					}
				}
			}
		})
	})

	$('.comments').on('click', 'li .vote-section .upvote', function(){
		$.ajax({
			url: '/upvote/comment/' + $(this).attr('id'),
			type: 'post',
			contentType: 'application/json',
			data: JSON.stringify({
				id: $(this).attr('id')
			}),
			success: function(response){
				if (response.redirect){
					window.location.href = response.redirect;
				}
				else {
					var vote_section = $('.comments').children(''.concat('#', response.id))
						.children('.vote-section').eq(0);
					vote_section.children(''.concat('#comment', response.id, 'vote-count')).text(response.data);
					var upvote_btn = vote_section.children('.upvote');
					var downvote_btn = vote_section.children('.downvote');
					switch (response.status) {
						case 'UP':
							upvote_btn.css('color', '#c64600');
							downvote_btn.css('color', '#9a9996');
							break;
						default:
							upvote_btn.css('color', '#9a9996');
					}
				}
			}
		})
	})

	$('.comments').on('click', 'li .vote-section .downvote', function(){
		$.ajax({
			url: '/downvote/comment/' + $(this).attr('id'),
			type: 'post',
			contentType: 'application/json',
			data: JSON.stringify({
				id: $(this).attr('id')
			}),
			success: function(response){
				if (response.redirect){
					window.location.href = response.redirect;
				} 
				else {
					var vote_section = $('.comments').children(''.concat('#', response.id))
						.children('.vote-section').eq(0);
					var upvote_btn = vote_section.children('.upvote');
					var downvote_btn = vote_section.children('.downvote');
					vote_section.children(''.concat('#comment', response.id, 'vote-count')).text(response.data);

					switch (response.status) {
						case 'DOWN':
							upvote_btn.css('color', '#9a9996');
							downvote_btn.css('color', '#003399');
							break;
						default:
							downvote_btn.css('color', '#9a9996');
					}
				}
			}
		})
	})
})
