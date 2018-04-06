# -*- coding: utf-8 -*-
"""
attention module of Residual Attention Network
"""
import abc
import tensorflow as tf
from keras.layers.convolutional import UpSampling2D

from .basic_layers import ResidualBlock


class AttentionModule52(object):
    """AttentionModuleClass"""
    def __init__(self, p=1, t=2, r=1, scope="attention_module"):
        """
        :param p: the number of pre-processing Residual Units before splitting into trunk branch and mask branch
        :param t: the number of Residual Units in trunk branch
        :param r: the number of Residual Units between adjacent pooling layer in the mask branch
        """
        self.p = p
        self.t = t
        self.r = r
        self.scope = scope

        self.residual_block = ResidualBlock()

    @abc.abstractmethod
    def soft_mask_branch(self, input, input_channels, is_training=True):
        """
        soft mask branch.
        :param input: A Tensor. input data [batch_size, height, width, channel]
        :param input_channels: dimension of input channel.
        :param is_training: boolean, whether training step or not(test step)
        :return: A Tensor [batch_size, height, width, channel]
        """
        return  input

    def f_prop(self, input, input_channels, is_training=True):
        """
        f_prop function of attention module
        :param input: A Tensor. input data [batch_size, height, width, channel]
        :param input_channels: dimension of input channel.
        :param is_training: boolean, whether training step or not(test step)
        :return: A Tensor [batch_size, height, width, channel]
        """
        with tf.variable_scope(self.scope):

            # residual blocks(TODO: change this function)
            with tf.variable_scope("first_residual_blocks"):
                for i in range(self.p):
                    input = self.residual_block.f_prop(input, input_channels, scope="num_blocks_{}".format(i), is_training=is_training)

            with tf.variable_scope("trunk_branch"):
                output_trunk = input
                for i in range(self.t):
                    output_trunk = self.residual_block.f_prop(output_trunk, input_channels, scope="num_blocks_{}".format(i), is_training=is_training)

            output_soft_mask = self.soft_mask_branch(input, input_channels, is_training=True)

            with tf.variable_scope("attention"):
                output = (1.0 + output_soft_mask) * output_trunk

            with tf.variable_scope("last_residual_blocks"):
                for i in range(self.p):
                    output = self.residual_block.f_prop(output, input_channels, scope="num_blocks_{}".format(i), is_training=is_training)

            return output


class AttentionModule52_1(AttentionModule52):
    """
    attention module stage 1
    """
    def __init__(self, p=1, t=2, r=1, scope="attention_module"):
        super().__init__(p=p, t=t, r=r, scope=scope)

    def soft_mask_branch(self, input, input_channels, is_training=True):
        """
        soft mask branch.
        :param input: A Tensor. input data [batch_size, height, width, channel]
        :param input_channels: dimension of input channel.
        :param is_training: boolean, whether training step or not(test step)
        :return: A Tensor [batch_size, height, width, channel]
        """
        with tf.variable_scope("soft_mask_branch"):

            with tf.variable_scope("down_sampling_1"):
                # max pooling
                filter_ = [1, 2, 2, 1]
                output_soft_mask = tf.nn.max_pool(input, ksize=filter_, strides=filter_, padding='SAME')

                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

            with tf.variable_scope("skip_connection_1"):
                # TODO(define new blocks)
                output_skip_connection_1 = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                    is_training=is_training)

            with tf.variable_scope("down_sampling_2"):
                # max pooling
                filter_ = [1, 2, 2, 1]
                output_soft_mask = tf.nn.max_pool(output_soft_mask, ksize=filter_, strides=filter_, padding='SAME')

                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

            with tf.variable_scope("skip_connection_2"):
                # TODO(define new blocks)
                output_skip_connection_2 = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                    is_training=is_training)


            with tf.variable_scope("down_sampling_3"):
                # max pooling
                filter_ = [1, 2, 2, 1]
                output_soft_mask = tf.nn.max_pool(output_soft_mask, ksize=filter_, strides=filter_, padding='SAME')

                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

            with tf.variable_scope("up_sampling_1"):
                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

                # interpolation # TODO change this function
                output_soft_mask = UpSampling2D([2, 2])(output_soft_mask)

            # add skip connection
            output_soft_mask += output_skip_connection_2

            with tf.variable_scope("up_sampling_2"):
                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

                # interpolation # TODO change this function
                output_soft_mask = UpSampling2D([2, 2])(output_soft_mask)

                # add skip connection
                output_soft_mask += output_skip_connection_1

            with tf.variable_scope("up_sampling_3"):
                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

                # interpolation # TODO change this function
                output_soft_mask = UpSampling2D([2, 2])(output_soft_mask)

            with tf.variable_scope("output"):
                output_soft_mask = tf.layers.conv2d(output_soft_mask, filters=input_channels, kernel_size=1)
                output_soft_mask = tf.layers.conv2d(output_soft_mask, filters=input_channels, kernel_size=1)

            # sigmoid
            return tf.nn.sigmoid(output_soft_mask)


class AttentionModule52_2(AttentionModule52):
    """
    attention module stage 2
    """
    def __init__(self, p=1, t=2, r=1, scope="attention_module"):
        super().__init__(p=p, t=t, r=r, scope=scope)

    def soft_mask_branch(self, input, input_channels, is_training=True):
        """
        soft mask branch.
        :param input: A Tensor. input data [batch_size, height, width, channel]
        :param input_channels: dimension of input channel.
        :param is_training: boolean, whether training step or not(test step)
        :return: A Tensor [batch_size, height, width, channel]
        """
        with tf.variable_scope("soft_mask_branch"):

            with tf.variable_scope("down_sampling_1"):
                # max pooling ->[batch, height/2, weight/2, channel]
                filter_ = [1, 2, 2, 1]
                output_soft_mask = tf.nn.max_pool(input, ksize=filter_, strides=filter_, padding='SAME')

                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

            with tf.variable_scope("skip_connection_1"):
                output_skip_connection_1 = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                    is_training=is_training)

            with tf.variable_scope("down_sampling_2"):
                # max pooling ->[batch, height/4, weight/4, channel]
                filter_ = [1, 2, 2, 1]
                output_soft_mask = tf.nn.max_pool(output_soft_mask, ksize=filter_, strides=filter_, padding='SAME')

                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

            with tf.variable_scope("up_sampling_1"):
                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

                # interpolation # TODO change this function
                output_soft_mask = UpSampling2D([2, 2])(output_soft_mask)

            # add skip connection
            output_soft_mask += output_skip_connection_1

            with tf.variable_scope("up_sampling_2"):
                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

                # interpolation # TODO change this function
                output_soft_mask = UpSampling2D([2, 2])(output_soft_mask)

            with tf.variable_scope("output"):
                output_soft_mask = tf.layers.conv2d(output_soft_mask, filters=input_channels, kernel_size=1)
                output_soft_mask = tf.layers.conv2d(output_soft_mask, filters=input_channels, kernel_size=1)

            # sigmoid
            return tf.nn.sigmoid(output_soft_mask)


class AttentionModule52_3(AttentionModule52):
    """
    attention module stage 3
    """
    def __init__(self, p=1, t=2, r=1, scope="attention_module"):
        super().__init__(p=p, t=t, r=r, scope=scope)

    def soft_mask_branch(self, input, input_channels, is_training=True):
        """
        soft mask branch.
        :param input: A Tensor. input data [batch_size, height, width, channel]
        :param input_channels: dimension of input channel.
        :param is_training: boolean, whether training step or not(test step)
        :return: A Tensor [batch_size, height, width, channel]
        """
        with tf.variable_scope("soft_mask_branch"):

            with tf.variable_scope("down_sampling_1"):
                # max pooling
                filter_ = [1, 2, 2, 1]
                output_soft_mask = tf.nn.max_pool(input, ksize=filter_, strides=filter_, padding='SAME')

                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

            with tf.variable_scope("up_sampling_1"):
                for i in range(self.r):
                    output_soft_mask = self.residual_block.f_prop(output_soft_mask, input_channels,
                                                                  scope="num_blocks_{}".format(i),
                                                                  is_training=is_training)

                # interpolation # TODO change this function
                output_soft_mask = UpSampling2D([2, 2])(output_soft_mask)

            with tf.variable_scope("output"):
                output_soft_mask = tf.layers.conv2d(output_soft_mask, filters=input_channels, kernel_size=1)
                output_soft_mask = tf.layers.conv2d(output_soft_mask, filters=input_channels, kernel_size=1)

            # sigmoid
            return tf.nn.sigmoid(output_soft_mask)