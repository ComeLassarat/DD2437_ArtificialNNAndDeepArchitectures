from util import *
from tqdm import tqdm


class RestrictedBoltzmannMachine:

    def __init__(self, ndim_visible, ndim_hidden, is_bottom=False, image_size=None, is_top=False, n_labels=10,
                 batch_size=10):

        """
        Args:
          ndim_visible: Number of units in visible layer.
          ndim_hidden: Number of units in hidden layer.

          is_bottom: True only if this rbm is at the bottom of the stack in a deep belief net. Used to interpret visible
          layer as image data with dimensions "image_size".

          image_size: Image dimension for visible layer.

          is_top: True only if this rbm is at the top of stack in deep beleif net. Used to interpret visible layer as
          concatenated with "n_label" unit of label data at the end.

          n_labels: Number of label categories.
          batch_size: Size of mini-batch.
        """

        if image_size is None:
            image_size = [28, 28]
        self.ndim_visible = ndim_visible
        self.ndim_hidden = ndim_hidden

        self.is_bottom = is_bottom
        if is_bottom:
            self.image_size = image_size

        self.is_top = is_top
        if is_top:
            self.n_labels = 10

        self.batch_size = batch_size
        self.learning_rate = 0.01
        self.momentum = 0.7
        self.print_period = 5000

        # initialization of weights and bias related variables
        self.delta_bias_v = 0
        self.delta_weight_vh = 0
        self.delta_bias_h = 0
        self.bias_v = np.random.normal(loc=0.0, scale=0.01, size=self.ndim_visible)
        self.weight_vh = np.random.normal(loc=0.0, scale=0.01, size=(self.ndim_visible, self.ndim_hidden))
        self.bias_h = np.random.normal(loc=0.0, scale=0.01, size=self.ndim_hidden)
        self.delta_weight_v_to_h = 0
        self.delta_weight_h_to_v = 0
        self.weight_v_to_h = None
        self.weight_h_to_v = None
        

        self.rf = {  # receptive-fields. Only applicable when visible layer is input data
            "period": 5000,  # iteration period to visualize
            "grid": [5, 5],  # size of the grid
            "ids": np.random.randint(0, self.ndim_hidden, 25)  # pick some random hidden units
        }

        return

    def cd1(self, visible_trainset, n_iterations=100, plotting=False):

        """Contrastive Divergence with k=1 full alternating Gibbs sampling

        Args:
          visible_trainset: training data for this rbm, shape is (size of training set, size of visible layer)
          n_iterations: number of iterations of learning (each iteration learns a mini-batch)
          plotting: set to True to plot (default = True)
        """
        averages_loss = []
        n_samples = visible_trainset.shape[0]
        loss_list = []
        error = []  # Storing error per iteration
        Nb_batch = int(n_samples / self.batch_size)
        current_epoch = 1  # Initialize current epoch as the first one
        for iteration in range(n_iterations):
            results_list = []
            for id_batch in tqdm(range(Nb_batch)): #tqdm initialize a process bar (woula c'est plus classe avec ??a)
            #for id_batch in range(Nb_batch):
                # [TODO TASK 4.1] run k=1 alternating Gibbs sampling : v_0 -> h_0 ->  v_1 -> h_1. you may need to
                #  use the inference functions 'get_h_given_v' and 'get_v_given_h'. note that inference methods returns
                #  both probabilities and activations (samples from probablities) and you may have to decide when to use
                #  what.

                #index for working with batch 
                index_init = int(id_batch % Nb_batch)
                index_stop = int((index_init + 1) * self.batch_size)
                index_init *= self.batch_size

                # selection of visible layer
                v_0 = visible_trainset[index_init:index_stop, :]
                p_h_given_v_0, h_0 = self.get_h_given_v(v_0)
                # Negative phase
                p_v_given_h_0, v_1 = self.get_v_given_h(h_0)
                p_h_given_v_1, h_1 = self.get_h_given_v(v_1) # p_v_given_h_0 ou v_1 

                # [TODO TASK 4.1] update the parameters using function 'update_params'

                self.update_params(v_0, h_0, v_1, h_1) #v_1, h_1 ou p_v_given_h_1, p_h_given_v_0

                if plotting:
                    if current_epoch >= 1:
                        ## Restoring image ##
                        #calcul de h0 = activation[p(h|v0)]
                        hidden_restored = self.get_h_given_v(v_0)[1] 
                        # calcul de v1 = activation[p(v|h0)]
                        restored_image = self.get_v_given_h(hidden_restored)[1] 
                        #on calcule l'erreur entre l'image initiale et la sortie du RBM : v0 et v1
                        loss_function = np.linalg.norm(v_0 - restored_image) / self.batch_size
                        
                        ## si on a fini de parcourir 1 batch ##
                        if id_batch % self.batch_size == 0: 
                            error.append(loss_function / self.batch_size)

                        loss_list.append(loss_function)

                        ## si on est au dernier batch ##
                        if id_batch == Nb_batch - 1: 
                            # Last iteration before emptying the list
                            results_list.append(np.array(loss_list).sum() / len(loss_list))  # Append avg loss epoch
                            loss_list = []  # Empty list

                    #if it_batch % self.print_period == 0:
                    #     loss_function = np.linalg.norm(v_0 - v_1) / self.batch_size
                    #     print("\niteration=%7d recon_loss=%4.4f" % (it_batch, loss_function))

            current_epoch += 1  # Update current epoch
            averages_loss.append(results_list)

            if self.is_bottom:
                viz_rf(weights=self.weight_vh[:, self.rf["ids"]].reshape((self.image_size[0],
                self.image_size[1], -1)),
                it=iteration * n_iterations, grid=self.rf["grid"])

        if plotting:
            plt.plot(range(len(error)), error, color='r')
            plt.xlabel("Batch")
            plt.ylabel("Error")
            plt.title("Evolution of Error over Batch")
            plt.grid()
            plt.show()

        return averages_loss

    def update_params(self, v_0, h_0, v_k, h_k):

        """Update the weight and bias parameters.

        You could also add weight decay and momentum for weight updates.

        Args:
           v_0: activities or probabilities of visible layer (data to the rbm)
           h_0: activities or probabilities of hidden layer
           v_k: activities or probabilities of visible layer
           h_k: activities or probabilities of hidden layer
           all args have shape (size of mini-batch, size of respective layer)
        """

        # DONE
        # [TODO TASK 4.1] 
        # we get the gradients from the arguments (replace the 0s below)
        # + we update the weight and bias parameters

        self.delta_bias_v = self.learning_rate * (np.sum(v_0 - v_k, axis=0)) # /v_0.shape[0]
        self.delta_weight_vh = self.learning_rate * ((v_0.T @ h_0) - (v_k.T @ h_k))
        self.delta_bias_h = self.learning_rate * (np.sum(h_0 - h_k, axis=0))  #/h_0.shape[0]

        self.bias_v += self.delta_bias_v
        self.weight_vh += self.delta_weight_vh
        self.bias_h += self.delta_bias_h
        # fonction en place ; ne retourne rien et update les param??tres du self seulement 
        return

    def get_h_given_v(self, visible_minibatch):

        """Compute probabilities p(h|v) and activations h ~ p(h|v) 

        Uses undirected weight "weight_vh" and bias "bias_h"
        
        Args: 
           visible_minibatch: shape is (size of mini-batch, size of visible layer)
        Returns:        
           tuple ( p(h|v) , h) 
           both are shaped (size of mini-batch, size of hidden layer)
        """

        assert self.weight_vh is not None
        n_samples = visible_minibatch.shape[0]

        # DONE 
        # [TODO TASK 4.1] compute probabilities and activations
        #  (samples from probabilities) of hidden layer (replace the zeros below)

        p_h_given_v = sigmoid(visible_minibatch @ self.weight_vh + self.bias_h)
        h = sample_binary(p_h_given_v)

        return p_h_given_v, h

    def get_v_given_h(self, hidden_minibatch):

        """Compute probabilities p(v|h) and activations v ~ p(v|h)

        Uses undirected weight "weight_vh" and bias "bias_v"
        
        Args: 
           hidden_minibatch: shape is (size of mini-batch, size of hidden layer)
        Returns:        
           tuple ( p(v|h) , v) 
           both are shaped (size of mini-batch, size of visible layer)
        """

        assert self.weight_vh is not None

        n_samples = hidden_minibatch.shape[0]

        if self.is_top:

            """
            Here visible layer has both data and labels. Compute total input for each unit (identical for both cases), 
            and split into two parts, something like support[:, :-self.n_labels] and support[:, -self.n_labels:].
            Then, for both parts, use the appropriate activation function to get probabilities and a sampling method
            to get activities. The probabilities as well as activities can then 
            be concatenated back into a normal visible layer.
            """

            # DONE
            # [TODO TASK 4.1] compute probabilities and activations
            #  (samples from probabilities) of visible layer (replace the pass below). \
            # Note that this section can also be postponed until TASK 4.2, since in this task,
            # stand-alone RBMs do not contain labels in visible layer.

            support = hidden_minibatch @ self.weight_vh.T + self.bias_v

            # Create arrays
            p_v_given_h = np.ndarray(shape=support.shape)
            s = np.ndarray(shape=support.shape)

            # Compute probabilities only for visible layer
            p_v_given_h[:, :-self.n_labels] = sigmoid(support[:, :-self.n_labels])
            p_v_given_h[:, -self.n_labels:] = softmax(support[:, -self.n_labels:])
            s[:, :-self.n_labels] = sample_binary(p_v_given_h[:, :-self.n_labels])
            s[:, -self.n_labels:] = sample_categorical(p_v_given_h[:, -self.n_labels:])

        else:
            # DONE           
            # [TODO TASK 4.1] compute probabilities and activations (samples from probabilities)
            #  of visible layer (replace the pass and zeros below)
            # equation 11
            p_v_given_h = sigmoid(hidden_minibatch @ self.weight_vh.T + self.bias_v)
            s = sample_binary(p_v_given_h)

        return p_v_given_h, s

    """ rbm as a belief layer : the functions below do not have to be changed until running a deep belief net """

    def untwine_weights(self):

        self.weight_v_to_h = np.copy(self.weight_vh)
        self.weight_h_to_v = np.copy(np.transpose(self.weight_vh))
        self.weight_vh = None

    def get_h_given_v_dir(self, visible_minibatch):

        """Compute probabilities p(h|v) and activations h ~ p(h|v)

        Uses directed weight "weight_v_to_h" and bias "bias_h"
        
        Args: 
           visible_minibatch: shape is (size of mini-batch, size of visible layer)
        Returns:        
           tuple ( p(h|v) , h) 
           both are shaped (size of mini-batch, size of hidden layer)
        """

        assert self.weight_v_to_h is not None

        n_samples = visible_minibatch.shape[0]

        # DONE
        # [TODO TASK 4.2] perform same computation as the function 'get_h_given_v'
        #  but with directed connections (replace the zeros below)

        p_h_given_v_dir = sigmoid(visible_minibatch @ self.weight_v_to_h + self.bias_h)
        h = sample_binary(p_h_given_v_dir)

        return p_h_given_v_dir, h

    def get_v_given_h_dir(self, hidden_minibatch):

        """Compute probabilities p(v|h) and activations v ~ p(v|h)

        Uses directed weight "weight_h_to_v" and bias "bias_v"
        
        Args: 
           hidden_minibatch: shape is (size of mini-batch, size of hidden layer)
        Returns:        
           tuple ( p(v|h) , v) 
           both are shaped (size of mini-batch, size of visible layer)
        """

        assert self.weight_h_to_v is not None

        n_samples = hidden_minibatch.shape[0]

        if self.is_top:

            """
            Here visible layer has both data and labels. Compute total input for each unit (identical for both cases),
            and split into two parts, something like support[:, :-self.n_labels] and support[:, -self.n_labels:].
            Then, for both parts, use the appropriate activation function to get probabilities and a sampling method
            to get activities. The probabilities as well as activities can then be concatenated back 
            into a normal visible layer.
            """

            p_v_given_h_dir, s = 0, 0

            # DONE
            # [TODO TASK 4.2] Note that even though this function performs same
            #  computation as 'get_v_given_h' but with directed connections,
            # this case should never be executed : when the RBM is a part of a DBN and is at
            # the top, it will have not have directed connections.
            # Appropriate code here is to raise an error (replace pass below)
            print("ERROR: P(V|H) directed 'is_top' = True")
            pass

        else:

            # DONE
            # [TODO TASK 4.2] performs same computaton as the function 'get_v_given_h' but
            #  with directed connections (replace the pass and zeros below)
            p_v_given_h_dir = sigmoid(hidden_minibatch @ self.weight_h_to_v + self.bias_v)
            s = sample_binary(p_v_given_h_dir)

        return p_v_given_h_dir, s

    # def update_generate_params(self, inps, trgs, preds):

    #     """Update generative weight "weight_h_to_v" and bias "bias_v"
        
    #     Args:
    #        inps: activities or probabilities of input unit
    #        trgs: activities or probabilities of output unit (target)
    #        preds: activities or probabilities of output unit (prediction)
    #        all args have shape (size of mini-batch, size of respective layer)
    #     """

    #     # DONE
    #     # [TODO TASK 4.3] find the gradients from the arguments (replace the 0s below)
    #     #  and update the weight and bias parameters.

    #     self.delta_weight_h_to_v = self.learning_rate * inps.T @ (trgs - preds)
    #     self.delta_bias_v = self.learning_rate * (np.sum(trgs - preds, axis=0)) 
        
    #     self.weight_h_to_v += self.delta_weight_h_to_v
    #     self.bias_v += self.delta_bias_v

    #     return

    # def update_recognize_params(self, inps, trgs, preds):

    #     """Update recognition weight "weight_v_to_h" and bias "bias_h"
        
    #     Args:
    #        inps: activities or probabilities of input unit
    #        trgs: activities or probabilities of output unit (target)
    #        preds: activities or probabilities of output unit (prediction)
    #        all args have shape (size of mini-batch, size of respective layer)
    #     """

    #     # DONE
    #     # [TODO TASK 4.3] find the gradients from the arguments (replace the 0s below) and
    #     #  update the weight and bias parameters.

    #     self.delta_weight_v_to_h = self.learning_rate * inps.T @ (trgs - preds)
    #     self.delta_bias_h = self.learning_rate * (np.sum(trgs - preds, axis=0))

    #     self.weight_v_to_h += self.delta_weight_v_to_h
    #     self.bias_h += self.delta_bias_h

    #     return
