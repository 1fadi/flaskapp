import unittest
from app import create_app, db
from app.models import User, Post, Role, Comment


class CommentModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        User.create_deleted_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_new_comment(self):
        u = User(username='john', email='john@example.com', password='cat')
        p = Post(title='test title', body='test body', author=u)
        c = Comment(body='test comment', post=p, author=u)
        db.session.add_all([u, p, c])
        db.session.commit()
        self.assertEqual(p.comments.count(), 1)
        self.assertTrue(p.comments.all()[-1] == c)
        self.assertTrue(u.comments.all()[-1] == c)
        self.assertTrue(c.vote_count == 0)
        u.upvote('comment', c)
        self.assertTrue(c.vote_count == 1)
        u.downvote('comment', c)
        self.assertTrue(c.vote_count == -1)

    def test_delete_comment(self):
        u = User(username='john', email='john@example.com', password='cat')
        p = Post(title='This is a test title', body='test body', author=u)
        c = Comment(body='test comment', post=p, author=u)
        db.session.add_all([u, p, c])
        db.session.commit()
        self.assertEqual(p.comments.count(), 1)
        db.session.delete(c)
        self.assertEqual(p.comments.count(), 0)
        self.assertEqual(u.comments.count(), 0)
